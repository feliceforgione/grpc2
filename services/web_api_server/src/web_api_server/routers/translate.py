from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from translate_proto.languages import convert_to_proto_language
from translate_proto.translator_pb2 import TranslateRequest
from translate_proto.translator_pb2_grpc import TranslationStub
from utils.language_name import LanguageName

GRPC_TIMEOUT_SECONDS = 5.0

translate_router = APIRouter(prefix="/api/translate", tags=["Translation"])


class TranslationRequestBody(BaseModel):
    text: str = Field(min_length=1)
    language: LanguageName


class TranslationResponseBody(BaseModel):
    translated_text: str


def get_translate_grpc_client(request: Request) -> TranslationStub:
    translate_grpc_client: TranslationStub = request.app.state.translate_grpc_client
    return translate_grpc_client


@translate_router.post("/")
async def translate(
    translation_request: TranslationRequestBody,
    translate_grpc_client: Annotated[TranslationStub, Depends(get_translate_grpc_client)],
) -> TranslationResponseBody:
    """Translate text into the requested language by calling the gRPC translation service."""
    translate_grpc_request = TranslateRequest(
        text=translation_request.text,
        language=convert_to_proto_language(translation_request.language),
    )
    translate_grpc_response = await translate_grpc_client.Translate(
        translate_grpc_request, timeout=GRPC_TIMEOUT_SECONDS
    )
    return TranslationResponseBody(translated_text=translate_grpc_response.translated_text)
