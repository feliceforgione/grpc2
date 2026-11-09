"""The Translation gRPC service, which validates each request and translates its text."""

import logging

import grpc
import grpc.aio

from translate_grpc.translation import translate_text
from translate_grpc.translation_provider import TranslationProvider
from translate_proto.languages import convert_language_name, is_supported_language
from translate_proto.translator_pb2 import TranslateRequest, TranslateResponse
from translate_proto.translator_pb2_grpc import (
    TranslationServicer,
    add_TranslationServicer_to_server,
)


class Translator(TranslationServicer):
    def __init__(self, translation_provider: TranslationProvider) -> None:
        self._translation_provider = translation_provider

    async def Translate(
        self,
        request: TranslateRequest,
        context: grpc.aio.ServicerContext[TranslateRequest, TranslateResponse],
    ) -> TranslateResponse:
        await self._validate_request_language(request.language, context)
        language = convert_language_name(request.language)
        try:
            translated_text = translate_text(self._translation_provider, request.text, language)
        except Exception:
            # Logged here, while the RPC's span is still current, so the error in Loki and
            # Sentry carries its trace ID. gRPC logs it again once the span has ended, which
            # Sentry drops as a duplicate.
            logging.exception(
                "Translation of %d characters to %s failed", len(request.text), language
            )
            raise
        # Logs the lengths rather than the text, which is the user's, as the spans do.
        logging.info(
            "Translated %d characters to %s, in %d characters",
            len(request.text),
            language,
            len(translated_text),
        )
        return TranslateResponse(translated_text=translated_text)

    async def _validate_request_language(
        self,
        language: int,
        context: grpc.aio.ServicerContext[TranslateRequest, TranslateResponse],
    ) -> None:
        if not is_supported_language(language):
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT, "language must be set to a supported value"
            )


def add_translation_service_to_server(
    server: grpc.aio.Server, translation_provider: TranslationProvider
) -> None:
    """Add the Translation service to the server."""
    add_TranslationServicer_to_server(  # type: ignore[no-untyped-call]
        Translator(translation_provider), server
    )
