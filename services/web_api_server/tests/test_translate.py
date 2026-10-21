from collections.abc import Iterator
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import Request
from fastapi.testclient import TestClient
from grpc import StatusCode
from grpc.aio import AioRpcError

from translate_proto.translator_pb2 import LANGUAGE_ITALIAN, TranslateRequest, TranslateResponse
from translate_proto.translator_pb2_grpc import TranslationStub
from utils.language_name import LanguageName
from web_api_server.main import app
from web_api_server.routers.translate import GRPC_TIMEOUT_SECONDS, get_translate_grpc_client

TRANSLATE_URL = "/api/translate/"
VALID_TEXT_TO_TRANSLATE = "hello"
VALID_LANGUAGE = LanguageName.ITALIAN
VALID_JSON_BODY = {"text": VALID_TEXT_TO_TRANSLATE, "language": VALID_LANGUAGE}


@pytest.fixture
def mock_translate_grpc_client() -> Iterator[Mock]:
    """Replace the gRPC client the route depends on with a mock whose `Translate` is async."""
    translate_grpc_client_mock = Mock(Translate=AsyncMock())
    app.dependency_overrides[get_translate_grpc_client] = lambda: translate_grpc_client_mock
    yield translate_grpc_client_mock
    app.dependency_overrides.clear()


@pytest.fixture
def web_server_client_with_server_side_grpc_client_mocked(
    mock_translate_grpc_client: Mock,
) -> TestClient:
    """Client for the app with the mock gRPC client in place.

    Not used as a context manager, so the lifespan never opens a real gRPC channel.
    """
    return TestClient(app)


def test_translate_returns_translated_text(
    web_server_client_with_server_side_grpc_client_mocked: TestClient,
    mock_translate_grpc_client: Mock,
) -> None:
    """A valid request is forwarded to gRPC and the translation is returned as JSON.

    Also checks the language name is converted to the proto enum and the timeout is passed.
    """
    mock_translate_grpc_client.Translate.return_value = TranslateResponse(
        translated_text="mock italian"
    )

    response = web_server_client_with_server_side_grpc_client_mocked.post(
        TRANSLATE_URL, json={"text": "mock", "language": LanguageName.ITALIAN}
    )

    assert response.status_code == 200
    assert response.json() == {"translated_text": "mock italian"}
    # The route must turn the "italian" LanguageName it received into the proto enum
    mock_translate_grpc_client.Translate.assert_awaited_once_with(
        TranslateRequest(text="mock", language=LANGUAGE_ITALIAN),
        timeout=GRPC_TIMEOUT_SECONDS,
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
        {"text": "", "language": VALID_LANGUAGE},  # text needs min_length=1
        {"text": VALID_TEXT_TO_TRANSLATE, "language": "klingon"},  # not a LanguageName value
        {
            "text": VALID_TEXT_TO_TRANSLATE,
            "language": VALID_LANGUAGE.upper(),
        },  # LanguageName is lowercase
        {"text": VALID_TEXT_TO_TRANSLATE},  # language is required
        {"language": VALID_LANGUAGE},  # text is required
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
    web_server_client_with_server_side_grpc_client_mocked: TestClient,
    mock_translate_grpc_client: Mock,
    body: dict[str, str],
) -> None:
    """A request body that fails validation gets 422 response & never reaches translate rpc."""
    response = web_server_client_with_server_side_grpc_client_mocked.post(TRANSLATE_URL, json=body)

    assert response.status_code == 422
    mock_translate_grpc_client.Translate.assert_not_awaited()


def test_empty_text_returns_422_flagging_text_as_too_short(
    web_server_client_with_server_side_grpc_client_mocked: TestClient,
    mock_translate_grpc_client: Mock,
) -> None:
    """An empty `text` gets a 422 response with one error in `detail`: `text` is too short."""
    empty_string = ""
    response = web_server_client_with_server_side_grpc_client_mocked.post(
        TRANSLATE_URL, json={"text": empty_string, "language": VALID_LANGUAGE}
    )

    assert response.status_code == 422
    [error] = response.json()["detail"]
    assert error["type"] == "string_too_short"
    assert error["loc"] == ["body", "text"]
    assert error["input"] == ""
    assert error["ctx"] == {"min_length": 1}
    mock_translate_grpc_client.Translate.assert_not_awaited()


def test_grpc_invalid_argument_returns_400_with_details(
    web_server_client_with_server_side_grpc_client_mocked: TestClient,
    mock_translate_grpc_client: Mock,
) -> None:
    """A gRPC INVALID_ARGUMENT becomes a 400 that passes the server's message to the client."""
    # The mock rejects every request, as the server would if it didn't support a language
    # the API accepts (e.g. one added to LanguageName before the gRPC server is updated).
    unsupported_language_grpc_error_details = "language must be set to a supported value"
    mock_translate_grpc_client.Translate.side_effect = AioRpcError(
        StatusCode.INVALID_ARGUMENT,
        Mock(),
        Mock(),
        details=unsupported_language_grpc_error_details,
        debug_error_string=None,
    )

    response = web_server_client_with_server_side_grpc_client_mocked.post(
        TRANSLATE_URL, json=VALID_JSON_BODY
    )

    assert response.status_code == 400
    assert response.json() == {"detail": unsupported_language_grpc_error_details}


def test_grpc_invalid_argument_without_details_returns_generic_400(
    web_server_client_with_server_side_grpc_client_mocked: TestClient,
    mock_translate_grpc_client: Mock,
) -> None:
    """A gRPC INVALID_ARGUMENT with no message becomes a 400 with a generic message."""
    mock_translate_grpc_client.Translate.side_effect = AioRpcError(
        StatusCode.INVALID_ARGUMENT, Mock(), Mock(), details=None, debug_error_string=None
    )

    response = web_server_client_with_server_side_grpc_client_mocked.post(
        TRANSLATE_URL, json=VALID_JSON_BODY
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
def test_web_server_replaces_grpc_server_error_details_with_generic_message_before_return_to_client(
    web_server_client_with_server_side_grpc_client_mocked: TestClient,
    mock_translate_grpc_client: Mock,
    code: StatusCode,
    http_status: int,
) -> None:
    """Server gRPC errors map to 5xx statuses & never expose server error message to web client."""
    mock_translate_grpc_client.Translate.side_effect = AioRpcError(
        code, Mock(), Mock(), details="secret internal details", debug_error_string=None
    )

    response = web_server_client_with_server_side_grpc_client_mocked.post(
        TRANSLATE_URL, json=VALID_JSON_BODY
    )

    assert response.status_code == http_status
    assert response.json() == {"detail": "Upstream service error"}
