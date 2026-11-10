"""The standard gRPC health service (`grpc.health.v1.Health`), shared by the gRPC servers.

Each server adds the service with `add_health_service_to_server`. Its health-check command,
which Docker runs, calls `run_grpc_health_check` with the server's port.
"""

import asyncio
import sys
from typing import NoReturn

from grpc.aio import AioRpcError, Server, insecure_channel
from grpc_health.v1._async import HealthServicer
from grpc_health.v1.health_pb2 import HealthCheckRequest, HealthCheckResponse
from grpc_health.v1.health_pb2_grpc import HealthStub, add_HealthServicer_to_server

from utils.constants import LOOPBACK_IPV4

HEALTH_CHECK_TIMEOUT_SECONDS = 3.0


async def add_health_service_to_server(server: Server) -> None:
    """Add the standard gRPC health service to the server, reporting SERVING for the
    server as a whole (""). It never calls the server's own services.
    """
    health_servicer = HealthServicer()
    await health_servicer.set("", HealthCheckResponse.SERVING)
    add_HealthServicer_to_server(health_servicer, server)


async def is_grpc_server_healthy(address: str) -> bool:
    """Return whether the gRPC server at `address` reports SERVING for the whole server."""
    async with insecure_channel(address) as channel:
        try:
            response = await HealthStub(channel).Check(
                HealthCheckRequest(), timeout=HEALTH_CHECK_TIMEOUT_SECONDS
            )
        except AioRpcError:
            return False
    # bool() for mypy: protobuf's enum metaclass makes this comparison type as Any.
    return bool(response.status == HealthCheckResponse.SERVING)


def run_grpc_health_check(port: int) -> NoReturn:
    """Check the gRPC server on this machine's `port`, and exit with 0 when it reports
    SERVING, or 1 when it reports anything else or doesn't answer in time.
    """
    server_address = f"{LOOPBACK_IPV4}:{port}"
    is_serving = asyncio.run(is_grpc_server_healthy(server_address))
    sys.exit(0 if is_serving else 1)
