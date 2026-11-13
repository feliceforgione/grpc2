"""The CharacterCounter gRPC service, which counts the characters in each request's text."""

import logging

from grpc import StatusCode
from grpc.aio import Server, ServicerContext

from character_count_grpc.character_count_metrics import (
    TEXT_TOO_LONG_ERROR_TYPE,
    record_text_length,
)
from character_count_proto.character_counter_pb2 import (
    CountCharactersRequest,
    CountCharactersResponse,
)
from character_count_proto.character_counter_pb2_grpc import (
    CharacterCounterServicer,
    add_CharacterCounterServicer_to_server,
)

MAX_CHARACTER_COUNT = 15


class CharacterCounter(CharacterCounterServicer):
    async def CountCharacters(
        self,
        request: CountCharactersRequest,
        context: ServicerContext[CountCharactersRequest, CountCharactersResponse],
    ) -> CountCharactersResponse:
        # len() counts Unicode code points, so "é" and "👋" each count as one character.
        character_count = len(request.text_to_count)
        if character_count > MAX_CHARACTER_COUNT:
            record_text_length(character_count, TEXT_TOO_LONG_ERROR_TYPE)
            # abort() raises, so the RPC ends here with an INVALID_ARGUMENT status.
            await context.abort(
                StatusCode.INVALID_ARGUMENT,
                f"Text has {character_count} characters; the maximum is {MAX_CHARACTER_COUNT}",
            )
        record_text_length(character_count)
        # Logs the count rather than the text.
        logging.info("Counted %d characters", character_count)
        return CountCharactersResponse(character_count=character_count)


def add_character_count_service_to_server(server: Server) -> None:
    """Add the CharacterCounter service to the server."""
    add_CharacterCounterServicer_to_server(  # type: ignore[no-untyped-call]
        CharacterCounter(), server
    )
