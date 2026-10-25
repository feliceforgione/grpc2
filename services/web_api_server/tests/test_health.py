from unittest.mock import Mock

from fastapi.testclient import TestClient
from grpc import StatusCode
from grpc.aio import AioRpcError

from web_api_server.main import app

HEALTH_ROUTE_URL = "/health"


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
