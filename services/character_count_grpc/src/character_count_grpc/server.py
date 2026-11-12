"""Entry point for the character count gRPC server: adds its services and serves them."""

import asyncio
import logging

from dotenv import load_dotenv
from grpc.aio import Server

from character_count_grpc.character_counter_servicer import add_character_count_service_to_server
from utils.constants import CHARACTER_COUNT_GRPC_SERVER_PORT
from utils.error_tracking import setup_error_tracking
from utils.grpc_health import add_health_service_to_server
from utils.grpc_server import create_grpc_server
from utils.telemetry import setup_telemetry


async def add_services_to_server(server: Server) -> None:
    """Add the CharacterCounter service and the standard gRPC health service to the server."""
    add_character_count_service_to_server(server)
    await add_health_service_to_server(server)


async def serve() -> None:
    server = create_grpc_server()
    await add_services_to_server(server)
    listen_address = f"[::]:{CHARACTER_COUNT_GRPC_SERVER_PORT}"
    server.add_insecure_port(listen_address)
    logging.info("Starting server on %s", listen_address)
    await server.start()
    await server.wait_for_termination()


def main() -> None:
    load_dotenv()
    logging.basicConfig(level=logging.INFO)
    setup_telemetry("character-count-grpc")
    setup_error_tracking("character-count-grpc")
    asyncio.run(serve())


if __name__ == "__main__":
    main()
