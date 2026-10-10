import os
from collections.abc import AsyncIterator

import grpc
import grpc.aio
import pytest
from dotenv import load_dotenv

# translate_grpc.translation reads OPENAI_API_KEY at import time. Load the real key
# from .env first (for live tests), then fall back to a dummy so the offline tests
# can import the server without one; they patch the translator out.
load_dotenv()
os.environ.setdefault("OPENAI_API_KEY", "test-key")


@pytest.fixture
async def channel() -> AsyncIterator[grpc.aio.Channel]:
    """Run the real Translator servicer on an ephemeral port and yield a client channel."""
    # Imported here because translate_grpc.translation needs OPENAI_API_KEY set above.
    from translate_grpc import server
    from translate_proto.translator_pb2_grpc import add_TranslationServicer_to_server

    grpc_server = grpc.aio.server()
    add_TranslationServicer_to_server(  # type: ignore[no-untyped-call]
        server.Translator(), grpc_server
    )
    port = grpc_server.add_insecure_port("127.0.0.1:0")
    await grpc_server.start()
    try:
        async with grpc.aio.insecure_channel(f"127.0.0.1:{port}") as ch:
            yield ch
    finally:
        await grpc_server.stop(None)
