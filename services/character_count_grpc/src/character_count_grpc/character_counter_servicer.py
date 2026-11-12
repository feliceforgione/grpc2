"""The CharacterCounter gRPC service, which counts the characters in each request's text."""

import logging

from grpc.aio import Server, ServicerContext

from character_count_proto.character_counter_pb2 import (
    CountCharactersRequest,
    CountCharactersResponse,
)
from character_count_proto.character_counter_pb2_grpc import (
    CharacterCounterServicer,
    add_CharacterCounterServicer_to_server,
)


class CharacterCounter(CharacterCounterServicer):
    async def CountCharacters(
        self,
        request: CountCharactersRequest,
        context: ServicerContext[CountCharactersRequest, CountCharactersResponse],
    ) -> CountCharactersResponse:
        # len() counts Unicode code points, so "é" and "👋" each count as one character.
        character_count = len(request.text_to_count)
        # Logs the count rather than the text, which is the user's.
        logging.info("Counted %d characters", character_count)
        return CountCharactersResponse(character_count=character_count)


def add_character_count_service_to_server(server: Server) -> None:
    """Add the CharacterCounter service to the server."""
    add_CharacterCounterServicer_to_server(  # type: ignore[no-untyped-call]
        CharacterCounter(), server
    )
