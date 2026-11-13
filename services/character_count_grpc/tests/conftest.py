from collections.abc import AsyncIterator

import pytest
from grpc.aio import Channel, insecure_channel

from character_count_grpc.server import add_services_to_server
from character_count_proto.character_counter_pb2_grpc import CharacterCounterStub
from utils.constants import LOOPBACK_IPV4
from utils.grpc_server import create_grpc_server


@pytest.fixture
async def character_count_grpc_channel() -> AsyncIterator[Channel]:
    """Run the real server's services on an ephemeral port and yield a client channel to it."""
    grpc_server = create_grpc_server()
    await add_services_to_server(grpc_server)
    port = grpc_server.add_insecure_port(f"{LOOPBACK_IPV4}:0")
    await grpc_server.start()
    try:
        async with insecure_channel(f"{LOOPBACK_IPV4}:{port}") as channel:
            yield channel
    finally:
        await grpc_server.stop(None)


@pytest.fixture
def client(character_count_grpc_channel: Channel) -> CharacterCounterStub:
    """Client stub for the character count gRPC server."""
    return CharacterCounterStub(character_count_grpc_channel)  # type: ignore[no-untyped-call]
