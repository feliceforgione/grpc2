from collections.abc import Iterator
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi.testclient import TestClient
from grpc import StatusCode
from grpc.aio import AioRpcError

from utils.language_name import LanguageName
from web_api_server.main import app
from web_api_server.routers.translate import get_translate_grpc_client

LANGUAGES_ROUTE_URL = "/api/languages"


@pytest.fixture
def mock_translate_grpc_client() -> Iterator[Mock]:
    """Replace the gRPC translate client with a mock."""
    translate_grpc_client_mock = Mock(Translate=AsyncMock())
    app.dependency_overrides[get_translate_grpc_client] = lambda: translate_grpc_client_mock
    yield translate_grpc_client_mock
    app.dependency_overrides.clear()


def test_languages_route_returns_every_language_name_value() -> None:
    """`GET /api/languages` returns 200 with exactly the LanguageName values, in enum order."""
    response = TestClient(app).get(LANGUAGES_ROUTE_URL)

    assert response.status_code == 200
    assert response.json() == {"languages": [language.value for language in LanguageName]}

    # Check that value language is returned
    valid_language = "polish"
    assert LanguageName.POLISH in response.json()["languages"]
    assert valid_language in response.json()["languages"]


def test_languages_route_returns_languages_when_grpc_server_is_unreachable(
    mock_translate_grpc_client: Mock,
) -> None:
    """The languages route never calls gRPC servers, so it answers even when one is down."""
    mock_translate_grpc_client.Translate.side_effect = AioRpcError(
        StatusCode.UNAVAILABLE, Mock(), Mock(), details=None, debug_error_string=None
    )
    response = TestClient(app).get(LANGUAGES_ROUTE_URL)

    assert response.status_code == 200
    assert response.json() == {"languages": [language.value for language in LanguageName]}
    mock_translate_grpc_client.Translate.assert_not_awaited()
