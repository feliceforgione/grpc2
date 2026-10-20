"""FastAPI app for the web API server."""

import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from grpc.aio import AioRpcError, insecure_channel

from translate_proto.translator_pb2_grpc import TranslationStub
from web_api_server.grpc_errors import handle_grpc_error_response
from web_api_server.routers import health_router, languages_router, translate_router

TRANSLATE_GRPC_SERVER_ADDRESS = os.environ.get("TRANSLATE_GRPC_SERVER_ADDRESS", "localhost:50051")
WEB_API_SERVER_HOST = os.environ.get("WEB_API_SERVER_HOST", "127.0.0.1")
WEB_API_SERVER_PORT = int(os.environ.get("WEB_API_SERVER_PORT", "8000"))


@asynccontextmanager
async def app_lifespan(fastapi_app: FastAPI) -> AsyncGenerator[None]:
    """Open one gRPC channel for the app's lifetime and share it across requests."""
    async with insecure_channel(TRANSLATE_GRPC_SERVER_ADDRESS) as grpc_channel:
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


def main() -> None:
    """Run the app with uvicorn on WEB_API_SERVER_HOST and WEB_API_SERVER_PORT."""
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host=WEB_API_SERVER_HOST, port=WEB_API_SERVER_PORT)


if __name__ == "__main__":
    main()
