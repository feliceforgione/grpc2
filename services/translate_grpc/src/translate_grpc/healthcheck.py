"""Command that checks whether the gRPC server is up.

It calls the standard gRPC health service and exits with 0 when the server reports
SERVING, or 1 when it reports anything else or doesn't answer in time.
"""

import asyncio
import sys

from grpc.aio import AioRpcError, insecure_channel
from grpc_health.v1.health_pb2 import HealthCheckRequest, HealthCheckResponse
from grpc_health.v1.health_pb2_grpc import HealthStub

from translate_grpc.settings import TRANSLATE_GRPC_SERVER_PORT

HEALTH_CHECK_TIMEOUT_SECONDS = 3.0


async def check_grpc_server_health(address: str) -> bool:
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


def main() -> None:
    """Check the server on this machine's TRANSLATE_GRPC_SERVER_PORT and exit 0 if serving."""
    is_serving = asyncio.run(check_grpc_server_health(f"localhost:{TRANSLATE_GRPC_SERVER_PORT}"))
    sys.exit(0 if is_serving else 1)


if __name__ == "__main__":
    main()
