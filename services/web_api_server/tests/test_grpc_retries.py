"""Test the translate gRPC channel retries the status codes designated as retryable.

A mocked stub would skip the channel and its retry policy entirely, so these tests run a real
gRPC server on an ephemeral port, backed by a mock Translation servicer that can fail on cue.
"""

from collections import deque
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest
from grpc import StatusCode
from grpc.aio import AioRpcError, server

from translate_proto.translator_pb2 import LANGUAGE_ITALIAN, TranslateRequest, TranslateResponse
from translate_proto.translator_pb2_grpc import TranslationStub, add_TranslationServicer_to_server
from web_api_server.grpc_channel import MAX_ATTEMPTS, open_translate_grpc_channel
from web_api_server.routers.translate import GRPC_TIMEOUT_SECONDS

VALID_TRANSLATE_REQUEST = TranslateRequest(text="hello", language=LANGUAGE_ITALIAN)
VALID_TRANSLATED_TEXT = "ciao"


@pytest.fixture
async def mock_translation_servicer() -> AsyncIterator[Mock]:
    """Serve a mock Translation servicer on an ephemeral port, stored on the mock as `address`.

    `Translate` is created before registering, because the server binds that method then.
    """
    translation_servicer_mock = Mock(Translate=AsyncMock())
    grpc_server = server()
    add_TranslationServicer_to_server(  # type: ignore[no-untyped-call]
        translation_servicer_mock, grpc_server
    )
    grpc_server_ephemeral_port = grpc_server.add_insecure_port("127.0.0.1:0")
    translation_servicer_mock.address = f"127.0.0.1:{grpc_server_ephemeral_port}"
    await grpc_server.start()
    yield translation_servicer_mock
    await grpc_server.stop(None)


async def call_translate_service(server_address: str) -> TranslateResponse:
    """Call Translate through the same channel the web API server opens."""
    async with open_translate_grpc_channel(server_address) as grpc_channel:
        translate_grpc_client = TranslationStub(grpc_channel)  # type: ignore[no-untyped-call]
        translate_grpc_response: TranslateResponse = await translate_grpc_client.Translate(
            VALID_TRANSLATE_REQUEST, timeout=GRPC_TIMEOUT_SECONDS
        )
        return translate_grpc_response


def create_translate_handler_for_status_codes(
    status_codes: list[StatusCode],
) -> Callable[[TranslateRequest, Any], Awaitable[TranslateResponse]]:
    """Build a Translate handler that answers each call with the next code in `status_codes`.

    It aborts with an error code and returns a translation for OK.
    """
    remaining_status_codes_queue = deque(status_codes)

    async def respond_to_translate(request: TranslateRequest, context: Any) -> TranslateResponse:
        status_code = remaining_status_codes_queue.popleft()
        if status_code != StatusCode.OK:
            await context.abort(status_code, f"fake {status_code.name}")
        return TranslateResponse(translated_text=VALID_TRANSLATED_TEXT)

    return respond_to_translate


@pytest.mark.parametrize(
    "retryable_status_code",
    [
        StatusCode.UNAVAILABLE,  # the server was down or the connection dropped
        StatusCode.RESOURCE_EXHAUSTED,  # the server was overloaded
    ],
)
async def test_retryable_error_is_retried_until_success(
    mock_translation_servicer: Mock, retryable_status_code: StatusCode
) -> None:
    """A call that fails with a retryable code on every attempt but the last still succeeds."""
    mock_translation_servicer.Translate.side_effect = create_translate_handler_for_status_codes(
        [retryable_status_code] * (MAX_ATTEMPTS - 1) + [StatusCode.OK]
    )

    translate_grpc_response = await call_translate_service(mock_translation_servicer.address)

    assert translate_grpc_response.translated_text == VALID_TRANSLATED_TEXT
    assert mock_translation_servicer.Translate.await_count == MAX_ATTEMPTS


async def test_retryable_error_fails_after_max_attempts(mock_translation_servicer: Mock) -> None:
    """A retryable code that never clears stops being retried after MAX_ATTEMPTS calls."""
    mock_translation_servicer.Translate.side_effect = create_translate_handler_for_status_codes(
        [StatusCode.UNAVAILABLE] * MAX_ATTEMPTS
    )

    with pytest.raises(AioRpcError) as grpc_error:
        await call_translate_service(mock_translation_servicer.address)

    assert grpc_error.value.code() == StatusCode.UNAVAILABLE
    assert mock_translation_servicer.Translate.await_count == MAX_ATTEMPTS


@pytest.mark.parametrize(
    "non_retryable_status_code",
    [
        StatusCode.INVALID_ARGUMENT,  # the request itself is bad, so repeating it can't help
        StatusCode.INTERNAL,  # the server may have done part of the work before failing
        StatusCode.UNKNOWN,  # an uncaught server exception; same risk as INTERNAL
    ],
)
async def test_non_retryable_error_is_not_retried(
    mock_translation_servicer: Mock, non_retryable_status_code: StatusCode
) -> None:
    """A code outside the retry policy fails on the first attempt, even if a retry would work."""
    mock_translation_servicer.Translate.side_effect = create_translate_handler_for_status_codes(
        [non_retryable_status_code, StatusCode.OK]
    )

    with pytest.raises(AioRpcError) as grpc_error:
        await call_translate_service(mock_translation_servicer.address)

    assert grpc_error.value.code() == non_retryable_status_code
    mock_translation_servicer.Translate.assert_awaited_once()
