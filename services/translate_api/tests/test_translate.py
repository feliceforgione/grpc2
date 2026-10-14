from collections.abc import Iterator
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import Request
from fastapi.testclient import TestClient
from grpc import StatusCode
from grpc.aio import AioRpcError, Metadata

from translate_api.main import app
from translate_api.routers.translate import GRPC_TIMEOUT_SECONDS, get_translate_grpc_client
from translate_proto.translator_pb2 import LANGUAGE_ITALIAN, TranslateRequest, TranslateResponse
from translate_proto.translator_pb2_grpc import TranslationStub

TRANSLATE_URL = "/api/translate/"


@pytest.fixture
def grpc_client_for_translate_route_mock() -> Iterator[AsyncMock]:
    """Replace the gRPC client with a fake `Translate` method"""
    translate_grpc_client = Mock(Translate=AsyncMock())
    app.dependency_overrides[get_translate_grpc_client] = lambda: translate_grpc_client
    yield translate_grpc_client.Translate
    app.dependency_overrides.clear()


@pytest.fixture
def api_client_with_grpc_mock(grpc_client_for_translate_route_mock: AsyncMock) -> TestClient:
    """Client for the app with the fake gRPC client in place.

    Not used as a context manager, so the lifespan never opens a real gRPC channel.
    """
    return TestClient(app)


def build_grpc_error_for_translate_route_mock(code: StatusCode, details: str = "") -> AioRpcError:
    """Build the gRPC error the translate route mock raises to simulate a failed call."""
    return AioRpcError(code, Metadata(), Metadata(), details=details, debug_error_string=None)


def test_translate_returns_translated_text(
    api_client_with_grpc_mock: TestClient, grpc_client_for_translate_route_mock: AsyncMock
) -> None:
    """A valid request is forwarded to gRPC and the translation is returned as JSON.

    Also checks the language name is converted to the proto enum and the timeout is passed.
    """
    grpc_client_for_translate_route_mock.return_value = TranslateResponse(translated_text="ciao")

    response = api_client_with_grpc_mock.post(
        TRANSLATE_URL, json={"text": "hello", "language": "italian"}
    )

    assert response.status_code == 200
    assert response.json() == {"translated_text": "ciao"}
    grpc_client_for_translate_route_mock.assert_awaited_once_with(
        TranslateRequest(text="hello", language=LANGUAGE_ITALIAN), timeout=GRPC_TIMEOUT_SECONDS
    )


def test_api_lifespan_creates_translation_stub_for_dependency() -> None:
    """The lifespan creates a gRPC client that `get_translate_grpc_client` hands to endpoints.

    The other tests override the dependency, so this is the only one that runs the real wiring.
    Opening the channel doesn't connect to the server, so no gRPC server is needed.
    """
    with TestClient(app):
        translate_grpc_client = get_translate_grpc_client(Request({"type": "http", "app": app}))

    assert isinstance(translate_grpc_client, TranslationStub)


@pytest.mark.parametrize(
    "body",
    [
        {"text": "", "language": "italian"},
        {"text": "hello", "language": "klingon"},
        {"text": "hello", "language": "ITALIAN"},
        {"text": "hello"},
        {"language": "italian"},
    ],
    ids=[
        "empty-text",
        "unknown-language",
        "uppercase-language",
        "missing-language",
        "missing-text",
    ],
)
def test_invalid_request_body_is_rejected_without_calling_grpc(
    api_client_with_grpc_mock: TestClient,
    grpc_client_for_translate_route_mock: AsyncMock,
    body: dict[str, str],
) -> None:
    """A request body that fails validation gets a 422 from FastAPI and never reaches gRPC."""
    response = api_client_with_grpc_mock.post(TRANSLATE_URL, json=body)

    assert response.status_code == 422
    grpc_client_for_translate_route_mock.assert_not_awaited()


def test_empty_text_error_points_at_text_field(
    api_client_with_grpc_mock: TestClient, grpc_client_for_translate_route_mock: AsyncMock
) -> None:
    """An empty `text` gets a 422 whose single error names the `text` field as too short."""
    response = api_client_with_grpc_mock.post(
        TRANSLATE_URL, json={"text": "", "language": "italian"}
    )

    assert response.status_code == 422
    [error] = response.json()["detail"]
    assert error["type"] == "string_too_short"
    assert error["loc"] == ["body", "text"]
    assert error["input"] == ""
    assert error["ctx"] == {"min_length": 1}
    grpc_client_for_translate_route_mock.assert_not_awaited()


def test_grpc_invalid_argument_returns_400_with_details(
    api_client_with_grpc_mock: TestClient, grpc_client_for_translate_route_mock: AsyncMock
) -> None:
    """A gRPC INVALID_ARGUMENT becomes a 400 that passes the server's message to the client."""
    # The fake rejects every request, as the server would if it didn't support a language
    # the API accepts (e.g. one added to LanguageName before the gRPC server is updated).
    grpc_client_for_translate_route_mock.side_effect = build_grpc_error_for_translate_route_mock(
        StatusCode.INVALID_ARGUMENT, "language must be set to a supported value"
    )

    response = api_client_with_grpc_mock.post(
        TRANSLATE_URL, json={"text": "hello", "language": "italian"}
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "language must be set to a supported value"}


def test_grpc_invalid_argument_without_details_returns_generic_400(
    api_client_with_grpc_mock: TestClient, grpc_client_for_translate_route_mock: AsyncMock
) -> None:
    """A gRPC INVALID_ARGUMENT with no message becomes a 400 with a generic message."""
    grpc_client_for_translate_route_mock.side_effect = build_grpc_error_for_translate_route_mock(
        StatusCode.INVALID_ARGUMENT
    )

    response = api_client_with_grpc_mock.post(
        TRANSLATE_URL, json={"text": "hello", "language": "italian"}
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid request"}


@pytest.mark.parametrize(
    ("code", "http_status"),
    [
        (StatusCode.UNAVAILABLE, 503),
        (StatusCode.DEADLINE_EXCEEDED, 504),
        (StatusCode.UNKNOWN, 502),
        (StatusCode.INTERNAL, 502),
    ],
)
def test_grpc_server_errors_hide_details(
    api_client_with_grpc_mock: TestClient,
    grpc_client_for_translate_route_mock: AsyncMock,
    code: StatusCode,
    http_status: int,
) -> None:
    """Server-side gRPC errors map to 5xx statuses and never expose the server's message."""
    grpc_client_for_translate_route_mock.side_effect = build_grpc_error_for_translate_route_mock(
        code, "secret internal details"
    )

    response = api_client_with_grpc_mock.post(
        TRANSLATE_URL, json={"text": "hello", "language": "italian"}
    )

    assert response.status_code == http_status
    assert response.json() == {"detail": "Upstream service error"}
