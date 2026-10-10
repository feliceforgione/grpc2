import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Annotated

import grpc
import grpc.aio
import uvicorn
from fastapi import APIRouter, Depends, FastAPI, Request
from pydantic import BaseModel, Field

from translate_api.grpc_errors import GrpcErrorRoute
from translate_proto.languages import convert_to_proto_language
from translate_proto.translator_pb2 import TranslateRequest
from translate_proto.translator_pb2_grpc import TranslationStub
from translate_proto.utils import LanguageName

TRANSLATE_GRPC_SERVER_ADDRESS = os.environ.get("TRANSLATE_GRPC_SERVER_ADDRESS", "localhost:50051")
API_HOST = os.environ.get("TRANSLATE_API_HOST", "127.0.0.1")
API_PORT = int(os.environ.get("TRANSLATE_API_PORT", "8000"))
GRPC_TIMEOUT_SECONDS = 30.0


class TranslationRequestBody(BaseModel):
    text: str = Field(min_length=1)
    language: LanguageName


class TranslationResponseBody(BaseModel):
    translated_text: str


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Open one gRPC channel for the app's lifetime and share it across requests."""
    async with grpc.aio.insecure_channel(TRANSLATE_GRPC_SERVER_ADDRESS) as grpc_channel:
        app.state.translate_grpc_client = TranslationStub(grpc_channel)  # type: ignore[no-untyped-call]
        yield


app = FastAPI(title="Translate API", lifespan=lifespan)
# Routes that call gRPC services; their gRPC errors become HTTP error responses.
grpc_router = APIRouter(route_class=GrpcErrorRoute)
app.include_router(grpc_router)


def get_translate_grpc_client(request: Request) -> TranslationStub:
    translate_grpc_client: TranslationStub = request.app.state.translate_grpc_client
    return translate_grpc_client


@grpc_router.post("/api/translate")
async def translate(
    translation_request: TranslationRequestBody,
    translate_grpc_client: Annotated[TranslationStub, Depends(get_translate_grpc_client)],
) -> TranslationResponseBody:
    grpc_request = TranslateRequest(
        text=translation_request.text,
        language=convert_to_proto_language(translation_request.language),
    )
    grpc_response = await translate_grpc_client.Translate(
        grpc_request, timeout=GRPC_TIMEOUT_SECONDS
    )
    return TranslationResponseBody(translated_text=grpc_response.translated_text)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host=API_HOST, port=API_PORT)


if __name__ == "__main__":
    main()
