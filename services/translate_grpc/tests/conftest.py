import os
from collections.abc import AsyncIterator, Iterator
from unittest.mock import Mock, patch

import grpc
import grpc.aio
import pytest
from deep_translator import ChatGptTranslator
from dotenv import load_dotenv

# translate_grpc.translation reads OPENAI_API_KEY at import time. Load the real key
# from .env first (for live tests), then fall back to a dummy so the offline tests
# can import the server without one; they patch the translator out.
load_dotenv()
os.environ.setdefault("OPENAI_API_KEY", "test-key")


@pytest.fixture
def mock_chat_gpt_translator_translate() -> Iterator[Mock]:
    """Mock `ChatGptTranslator.translate` so the real translator is built but never calls OpenAI.

    autospec=True keeps the method signature, so each call receives the translator
    instance as its first argument;
    """
    with patch.object(ChatGptTranslator, "translate", autospec=True) as mock:
        yield mock


@pytest.fixture
async def server_address() -> AsyncIterator[str]:
    """Run the real server's services on an ephemeral port and yield its address."""
    # Imported here because translate_grpc.translation needs OPENAI_API_KEY set above.
    from translate_grpc.server import add_services_to_server

    grpc_server = grpc.aio.server()
    await add_services_to_server(grpc_server)
    port = grpc_server.add_insecure_port("127.0.0.1:0")
    await grpc_server.start()
    try:
        yield f"127.0.0.1:{port}"
    finally:
        await grpc_server.stop(None)


@pytest.fixture
async def channel(server_address: str) -> AsyncIterator[grpc.aio.Channel]:
    """Yield a client channel to the server from `server_address`."""
    async with grpc.aio.insecure_channel(server_address) as ch:
        yield ch
