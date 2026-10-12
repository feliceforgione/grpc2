import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from grpc.aio import AioRpcError, insecure_channel

from translate_api.grpc_errors import grpc_error_response
from translate_api.routers import translate_router
from translate_proto.translator_pb2_grpc import TranslationStub

TRANSLATE_GRPC_SERVER_ADDRESS = os.environ.get("TRANSLATE_GRPC_SERVER_ADDRESS", "localhost:50051")
API_HOST = os.environ.get("TRANSLATE_API_HOST", "127.0.0.1")
API_PORT = int(os.environ.get("TRANSLATE_API_PORT", "8000"))


@asynccontextmanager
async def lifespan(fastapi_app: FastAPI) -> AsyncGenerator[None]:
    """Open one gRPC channel for the app's lifetime and share it across requests."""
    async with insecure_channel(TRANSLATE_GRPC_SERVER_ADDRESS) as grpc_channel:
        fastapi_app.state.translate_grpc_client = TranslationStub(grpc_channel)  # type: ignore[no-untyped-call]
        yield


app = FastAPI(
    title="Translate API",
    lifespan=lifespan,
    exception_handlers={AioRpcError: grpc_error_response},
)
app.include_router(translate_router)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host=API_HOST, port=API_PORT)


if __name__ == "__main__":
    main()
