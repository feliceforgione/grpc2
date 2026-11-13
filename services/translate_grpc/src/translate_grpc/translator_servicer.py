"""The Translation gRPC service, which validates each request and translates its text."""

import logging

import grpc
import grpc.aio
from grpc.aio import AioRpcError

from character_count_proto.character_counter_pb2 import (
    CountCharactersRequest,
    CountCharactersResponse,
)
from character_count_proto.character_counter_pb2_grpc import CharacterCounterStub
from translate_grpc.translation import translate_text
from translate_grpc.translation_provider import TranslationProvider
from translate_proto.languages import convert_language_name, is_supported_language
from translate_proto.translator_pb2 import TranslateRequest, TranslateResponse
from translate_proto.translator_pb2_grpc import (
    TranslationServicer,
    add_TranslationServicer_to_server,
)


class Translator(TranslationServicer):
    def __init__(
        self,
        translation_provider: TranslationProvider,
        character_count_grpc_client: CharacterCounterStub,
    ) -> None:
        self._translation_provider = translation_provider
        self._character_count_grpc_client = character_count_grpc_client

    async def Translate(
        self,
        request: TranslateRequest,
        context: grpc.aio.ServicerContext[TranslateRequest, TranslateResponse],
    ) -> TranslateResponse:
        await self._validate_request_language(request.language, context)
        language = convert_language_name(request.language)
        # Counted before the model is called, so a text over the character limit is rejected
        # without paying for its translation.
        text_length = await self._count_characters(request.text, context)
        try:
            translated_text = translate_text(
                self._translation_provider, request.text, language, text_length=text_length
            )
        except Exception:
            # Logged here, while the RPC's span is still current, so the error in Loki and
            # Sentry carries its trace ID. gRPC logs it again once the span has ended, which
            # Sentry drops as a duplicate.
            logging.exception("Translation of %d characters to %s failed", text_length, language)
            raise
        # Logs the lengths rather than the text, which is the user's, as the spans do.
        # The translation is measured with len(), not the character count service, since a
        # translation over its character limit would otherwise fail after it was paid for.
        logging.info(
            "Translated %d characters to %s, in %d characters",
            text_length,
            language,
            len(translated_text),
        )
        return TranslateResponse(translated_text=translated_text)

    async def _count_characters(
        self,
        text: str,
        context: grpc.aio.ServicerContext[TranslateRequest, TranslateResponse],
    ) -> int:
        """Count the text's characters with the character count service.

        A failed count ends the RPC with the count's status code and details, so a text over
        the character limit reaches the caller as INVALID_ARGUMENT.
        """
        try:
            # Given what's left of the caller's deadline, so the count can't outlast the RPC.
            count_characters_response: CountCharactersResponse = (
                await self._character_count_grpc_client.CountCharacters(
                    CountCharactersRequest(text_to_count=text), timeout=context.time_remaining()
                )
            )
        except AioRpcError as count_characters_error:
            # abort() raises, so the RPC ends here.
            await context.abort(
                count_characters_error.code(), count_characters_error.details() or ""
            )
        return count_characters_response.character_count

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
    server: grpc.aio.Server,
    translation_provider: TranslationProvider,
    character_count_grpc_client: CharacterCounterStub,
) -> None:
    """Add the Translation service to the server."""
    add_TranslationServicer_to_server(  # type: ignore[no-untyped-call]
        Translator(translation_provider, character_count_grpc_client), server
    )
