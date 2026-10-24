"""FastAPI app for the web API server."""

import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from grpc.aio import AioRpcError
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from translate_proto.translator_pb2_grpc import TranslationStub
from utils.telemetry import setup_telemetry
from web_api_server.grpc_channel import open_translate_grpc_channel
from web_api_server.grpc_errors import handle_grpc_error_response
from web_api_server.routers import (
    WEBSITE_STATIC_DIR,
    health_router,
    languages_router,
    translate_router,
    website_router,
)

TRANSLATE_GRPC_SERVER_ADDRESS = os.environ.get("TRANSLATE_GRPC_SERVER_ADDRESS", "localhost:50051")
WEB_API_SERVER_HOST = os.environ.get("WEB_API_SERVER_HOST", "127.0.0.1")
WEB_API_SERVER_PORT = int(os.environ.get("WEB_API_SERVER_PORT", "8000"))


@asynccontextmanager
async def app_lifespan(fastapi_app: FastAPI) -> AsyncGenerator[None]:
    """Open one gRPC channel for the app's lifetime and share it across requests."""
    async with open_translate_grpc_channel(TRANSLATE_GRPC_SERVER_ADDRESS) as grpc_channel:
        fastapi_app.state.translate_grpc_client = TranslationStub(grpc_channel)  # type: ignore[no-untyped-call]
        yield


app = FastAPI(
    title="Translate API",
    lifespan=app_lifespan,
    exception_handlers={AioRpcError: handle_grpc_error_response},
)
app.include_router(health_router)
app.include_router(languages_router)
app.include_router(translate_router)
app.include_router(website_router)
app.mount("/static", StaticFiles(directory=WEBSITE_STATIC_DIR), name="static")
# Record a span for each request. The spans go nowhere until main() calls setup_telemetry().
# Skipping the ASGI receive/send spans leaves one span per request instead of three or more.
FastAPIInstrumentor.instrument_app(app, exclude_spans=["receive", "send"])


def main() -> None:
    """Run the app with uvicorn on WEB_API_SERVER_HOST and WEB_API_SERVER_PORT."""
    logging.basicConfig(level=logging.INFO)
    setup_telemetry("web-api-server")
    uvicorn.run(app, host=WEB_API_SERVER_HOST, port=WEB_API_SERVER_PORT)


if __name__ == "__main__":
    main()
