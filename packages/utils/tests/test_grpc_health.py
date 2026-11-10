from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import pytest
from grpc.aio import Server, insecure_channel, server
from grpc_health.v1._async import HealthServicer
from grpc_health.v1.health_pb2 import HealthCheckRequest, HealthCheckResponse
from grpc_health.v1.health_pb2_grpc import HealthStub, add_HealthServicer_to_server

from utils.constants import LOOPBACK_IPV4
from utils.grpc_health import (
    add_health_service_to_server,
    is_grpc_server_healthy,
    run_grpc_health_check,
)


@asynccontextmanager
async def serve_on_ephemeral_port(grpc_server: Server) -> AsyncIterator[str]:
    """Start the server on a free loopback port, yield its address, and stop it afterwards."""
    port = grpc_server.add_insecure_port(f"{LOOPBACK_IPV4}:0")
    await grpc_server.start()
    try:
        yield f"{LOOPBACK_IPV4}:{port}"
    finally:
        await grpc_server.stop(None)


@pytest.fixture
async def healthy_grpc_server_address() -> AsyncIterator[str]:
    """Run a server with the shared health service, and yield its address."""
    grpc_server = server()
    await add_health_service_to_server(grpc_server)
    async with serve_on_ephemeral_port(grpc_server) as address:
        yield address


@pytest.fixture
async def unhealthy_grpc_server_address() -> AsyncIterator[str]:
    """Run a server that is up but reports NOT_SERVING, and yield its address."""
    grpc_server = server()
    health_servicer = HealthServicer()
    await health_servicer.set("", HealthCheckResponse.NOT_SERVING)
    add_HealthServicer_to_server(health_servicer, grpc_server)
    async with serve_on_ephemeral_port(grpc_server) as address:
        yield address


async def test_health_service_reports_serving(healthy_grpc_server_address: str) -> None:
    """The added health service answers a `Health/Check` call with SERVING.

    The request leaves `service` empty, which asks about the server as a whole
    rather than about one named service.
    """
    async with insecure_channel(healthy_grpc_server_address) as channel:
        response = await HealthStub(channel).Check(HealthCheckRequest())

    assert response.status == HealthCheckResponse.SERVING


async def test_is_grpc_server_healthy_when_serving(healthy_grpc_server_address: str) -> None:
    assert await is_grpc_server_healthy(healthy_grpc_server_address)


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
def test_run_grpc_health_check_exit_code(is_serving: bool, exit_code: int) -> None:
    """Exits 0 when the server on this machine's port is serving, and 1 when it isn't."""
    mock_port = 12345

    with patch(
        "utils.grpc_health.is_grpc_server_healthy", AsyncMock(return_value=is_serving)
    ) as mock_is_grpc_server_healthy:
        with pytest.raises(SystemExit) as exc_info:
            run_grpc_health_check(mock_port)

    assert exc_info.value.code == exit_code
    mock_is_grpc_server_healthy.assert_awaited_once_with(f"{LOOPBACK_IPV4}:{mock_port}")
