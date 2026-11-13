"""Client for the character count gRPC server, which translate-grpc calls before translating."""

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from character_count_proto.character_counter_pb2_grpc import CharacterCounterStub
from utils.constants import CHARACTER_COUNT_GRPC_SERVER_PORT, LOOPBACK_IPV4
from utils.grpc_channel import open_grpc_channel

CHARACTER_COUNT_GRPC_SERVER_ADDRESS = os.environ.get(
    "CHARACTER_COUNT_GRPC_SERVER_ADDRESS", f"{LOOPBACK_IPV4}:{CHARACTER_COUNT_GRPC_SERVER_PORT}"
)


@asynccontextmanager
async def open_character_count_grpc_client() -> AsyncIterator[CharacterCounterStub]:
    """Open a channel to the character count server and yield a client stub that uses it.

    The channel closes when the `async with` block exits.
    """
    async with open_grpc_channel(CHARACTER_COUNT_GRPC_SERVER_ADDRESS) as character_count_channel:
        yield CharacterCounterStub(character_count_channel)  # type: ignore[no-untyped-call]
