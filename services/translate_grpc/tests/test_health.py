from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, patch

import grpc
import grpc.aio
import pytest
from grpc_health.v1._async import HealthServicer
from grpc_health.v1.health_pb2 import HealthCheckRequest, HealthCheckResponse
from grpc_health.v1.health_pb2_grpc import HealthStub, add_HealthServicer_to_server

from translate_grpc.healthcheck import is_grpc_server_healthy, main
from utils.constants import LOOPBACK_IPV4


@pytest.fixture
async def unhealthy_grpc_server_address() -> AsyncIterator[str]:
    """Run a server that is up but reports NOT_SERVING, and yield its address."""
    grpc_server = grpc.aio.server()
    health_servicer = HealthServicer()
    await health_servicer.set("", HealthCheckResponse.NOT_SERVING)
    add_HealthServicer_to_server(health_servicer, grpc_server)
    port = grpc_server.add_insecure_port(f"{LOOPBACK_IPV4}:0")
    await grpc_server.start()
    try:
        yield f"{LOOPBACK_IPV4}:{port}"
    finally:
        await grpc_server.stop(None)


async def test_health_check_reports_serving(translate_grpc_channel: grpc.aio.Channel) -> None:
    """The real server answers a `Health/Check` call with SERVING.

    Tests the server side: that the health service is registered and set to SERVING.
    The request leaves `service` empty, which asks about the server as a whole
    rather than about one named service.
    """
    response = await HealthStub(translate_grpc_channel).Check(HealthCheckRequest())

    assert response.status == HealthCheckResponse.SERVING


async def test_is_grpc_server_healthy_when_serving(translate_grpc_server_address: str) -> None:
    """Returns True when the server reports SERVING.

    Tests the client side: the helper the container health check runs, which
    turns the server's answer into a bool.
    """
    assert await is_grpc_server_healthy(translate_grpc_server_address)


async def test_is_grpc_server_healthy_when_not_serving(
    unhealthy_grpc_server_address: str,
) -> None:
    """Returns False when the server is up but reports NOT_SERVING."""
    assert not await is_grpc_server_healthy(unhealthy_grpc_server_address)


async def test_is_grpc_server_healthy_when_unreachable() -> None:
    """Returns False when nothing listens at the address.

    Port 1 is reserved and has no listener, so the connection is refused.
    """
    assert not await is_grpc_server_healthy(f"{LOOPBACK_IPV4}:1")


@pytest.mark.parametrize(
    ("is_serving", "exit_code"),
    [
        (True, 0),  # Docker marks the container healthy on exit code 0
        (False, 1),  # any non-zero exit code marks it unhealthy
    ],
)
def test_healthcheck_main_exit_code(is_serving: bool, exit_code: int) -> None:
    """`main()` exits 0 when the server is serving and 1 when it isn't."""
    with patch(
        "translate_grpc.healthcheck.is_grpc_server_healthy", AsyncMock(return_value=is_serving)
    ):
        with pytest.raises(SystemExit) as exc_info:
            main()

    assert exc_info.value.code == exit_code
