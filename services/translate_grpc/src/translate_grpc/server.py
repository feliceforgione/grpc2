"""Entry point for the translate gRPC server: adds its services and serves them."""

import asyncio
import logging

import grpc.aio

from translate_grpc.health_servicer import add_health_service_to_server
from translate_grpc.translator_servicer import add_translation_service_to_server
from utils.constants import TRANSLATE_GRPC_SERVER_PORT


async def add_services_to_server(server: grpc.aio.Server) -> None:
    """Add the Translation service and the standard gRPC health service to the server."""
    add_translation_service_to_server(server)
    await add_health_service_to_server(server)


async def serve() -> None:
    server = grpc.aio.server()
    await add_services_to_server(server)
    listen_addr = f"[::]:{TRANSLATE_GRPC_SERVER_PORT}"
    server.add_insecure_port(listen_addr)
    logging.info("Starting server on %s", listen_addr)
    await server.start()
    await server.wait_for_termination()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(serve())


if __name__ == "__main__":
    main()
