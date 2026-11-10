"""Entry point for the translate gRPC server: adds its services and serves them."""

import asyncio
import logging
import os

import grpc.aio
from dotenv import load_dotenv
from opentelemetry.instrumentation.grpc import aio_server_interceptor
from opentelemetry.instrumentation.grpc.filters import health_check, negate

from translate_grpc.deep_translator_provider import DeepTranslatorProvider
from translate_grpc.translation_provider import TranslationProvider
from translate_grpc.translator_servicer import add_translation_service_to_server
from utils.constants import TRANSLATE_GRPC_SERVER_PORT
from utils.error_tracking import setup_error_tracking
from utils.grpc_health import add_health_service_to_server
from utils.telemetry import setup_telemetry


def create_grpc_server() -> grpc.aio.Server:
    """Create a server that records a span for each RPC, except the health checks."""
    tracing_interceptor = aio_server_interceptor(  # type: ignore[no-untyped-call]
        filter_=negate(health_check())
    )
    return grpc.aio.server(interceptors=[tracing_interceptor])


async def add_services_to_server(
    server: grpc.aio.Server, translation_provider: TranslationProvider
) -> None:
    """Add the Translation service and the standard gRPC health service to the server."""
    add_translation_service_to_server(server, translation_provider)
    await add_health_service_to_server(server)


async def serve(translation_provider: TranslationProvider) -> None:
    server = create_grpc_server()
    await add_services_to_server(server, translation_provider)
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
