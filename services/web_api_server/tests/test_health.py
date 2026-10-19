from collections.abc import Iterator
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi.testclient import TestClient
from grpc import StatusCode
from grpc.aio import AioRpcError

from web_api_server.main import app
from web_api_server.routers.translate import get_translate_grpc_client

HEALTH_ROUTE_URL = "/health"


@pytest.fixture
def mock_translate_grpc_client() -> Iterator[Mock]:
    """Replace the gRPC translate client with a mock."""
    translate_grpc_client_mock = Mock(Translate=AsyncMock())
    app.dependency_overrides[get_translate_grpc_client] = lambda: translate_grpc_client_mock
    yield translate_grpc_client_mock
    app.dependency_overrides.clear()


def test_health_route_returns_ok() -> None:
    """`GET /health` returns 200 with `{"status": "ok"}`."""
    response = TestClient(app).get(HEALTH_ROUTE_URL)

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_route_returns_ok_when_grpc_server_is_unreachable(
    mock_translate_grpc_client: Mock,
) -> None:
    """The health route never calls gRPC servers, so it returns ok even when one is down."""
    mock_translate_grpc_client.Translate.side_effect = AioRpcError(
        StatusCode.UNAVAILABLE, Mock(), Mock(), details=None, debug_error_string=None
    )
    response = TestClient(app).get(HEALTH_ROUTE_URL)

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    mock_translate_grpc_client.Translate.assert_not_awaited()
