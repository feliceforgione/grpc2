"""Entry point for the translate gRPC server: adds its services and serves them."""

import asyncio
import logging
import os

import grpc.aio
from dotenv import load_dotenv

from character_count_proto.character_counter_pb2_grpc import CharacterCounterStub
from translate_grpc.character_count_client import open_character_count_grpc_client
from translate_grpc.deep_translator_provider import DeepTranslatorProvider
from translate_grpc.translation_provider import TranslationProvider
from translate_grpc.translator_servicer import add_translation_service_to_server
from utils.constants import TRANSLATE_GRPC_SERVER_PORT
from utils.error_tracking import setup_error_tracking
from utils.grpc_health import add_health_service_to_server
from utils.grpc_server import create_grpc_server
from utils.telemetry import setup_telemetry


async def add_services_to_server(
    server: grpc.aio.Server,
    translation_provider: TranslationProvider,
    character_count_grpc_client: CharacterCounterStub,
) -> None:
    """Add the Translation service and the standard gRPC health service to the server."""
    add_translation_service_to_server(server, translation_provider, character_count_grpc_client)
    await add_health_service_to_server(server)


async def serve(translation_provider: TranslationProvider) -> None:
    # One channel to the character count server, open for the server's lifetime and shared
    # by every RPC.
    async with open_character_count_grpc_client() as character_count_grpc_client:
        server = create_grpc_server()
        await add_services_to_server(server, translation_provider, character_count_grpc_client)
        listen_addr = f"[::]:{TRANSLATE_GRPC_SERVER_PORT}"
        server.add_insecure_port(listen_addr)
        logging.info("Starting server on %s", listen_addr)
        await server.start()
        await server.wait_for_termination()


def main() -> None:
    load_dotenv()
    logging.basicConfig(level=logging.INFO)
    setup_telemetry("translate-grpc")
    setup_error_tracking("translate-grpc")

    # The translation provider is chosen here, the one place that builds it
    translation_provider: TranslationProvider = DeepTranslatorProvider(
        api_key=os.environ["OPENAI_API_KEY"]
    )
    asyncio.run(serve(translation_provider))


if __name__ == "__main__":
    main()
