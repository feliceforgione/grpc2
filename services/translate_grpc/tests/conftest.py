from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, Mock

import grpc
import grpc.aio
import pytest

from character_count_proto.character_counter_pb2 import CountCharactersResponse
from translate_grpc.server import add_services_to_server
from translate_grpc.translation_provider import TranslationProvider
from utils.constants import LOOPBACK_IPV4
from utils.grpc_server import create_grpc_server


@pytest.fixture
def mock_translation_provider() -> Mock:
    """A provider that never calls a model"""
    mock_translation_provider = Mock(spec=TranslationProvider)
    mock_translation_provider.PROVIDER_NAME = "mock-provider"
    mock_translation_provider.MODEL = "mock-model"
    return mock_translation_provider


@pytest.fixture
def translation_provider(mock_translation_provider: Mock) -> TranslationProvider:
    """The provider the test server translates with.

    Override it to use a real provider for integration tests.
    """
    return mock_translation_provider


@pytest.fixture
def mock_character_count_grpc_client() -> Mock:
    """A character count client that never calls the character count server.

    It counts every text as 5 characters; tests that check the count set their own.
    """
    mock_character_count_grpc_client = Mock()
    mock_character_count_grpc_client.CountCharacters = AsyncMock(
        return_value=CountCharactersResponse(character_count=5)
    )
    return mock_character_count_grpc_client


@pytest.fixture
async def translate_grpc_server_address(
    translation_provider: TranslationProvider, mock_character_count_grpc_client: Mock
) -> AsyncIterator[str]:
    """Run the real server's services on an ephemeral port and yield its address."""
    grpc_server = create_grpc_server()
    await add_services_to_server(
        grpc_server, translation_provider, mock_character_count_grpc_client
    )
    port = grpc_server.add_insecure_port(f"{LOOPBACK_IPV4}:0")
    await grpc_server.start()
    try:
        yield f"{LOOPBACK_IPV4}:{port}"
    finally:
        await grpc_server.stop(None)


@pytest.fixture
async def translate_grpc_channel(
    translate_grpc_server_address: str,
) -> AsyncIterator[grpc.aio.Channel]:
    """Yield a client channel to the translate gRPC server at `translate_grpc_server_address`."""
    async with grpc.aio.insecure_channel(translate_grpc_server_address) as translate_grpc_channel:
        yield translate_grpc_channel
