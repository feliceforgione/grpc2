"""The gRPC health service (`grpc.health.v1.Health`) for the translate server."""

import grpc.aio
from grpc_health.v1._async import HealthServicer
from grpc_health.v1.health_pb2 import HealthCheckResponse
from grpc_health.v1.health_pb2_grpc import add_HealthServicer_to_server


async def add_health_service_to_server(server: grpc.aio.Server) -> None:
    """Add the standard gRPC health service to the server, reporting SERVING for the
    server as a whole (""). It never calls the translator.
    """
    health_servicer = HealthServicer()
    await health_servicer.set("", HealthCheckResponse.SERVING)
    add_HealthServicer_to_server(health_servicer, server)
