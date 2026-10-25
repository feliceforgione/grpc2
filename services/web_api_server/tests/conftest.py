from collections.abc import AsyncIterator, Callable, Iterator
from unittest.mock import AsyncMock, Mock

import pytest
from grpc.aio import server

from translate_proto.translator_pb2_grpc import TranslationStub, add_TranslationServicer_to_server
from utils.constants import LOOPBACK_IPV4
from web_api_server.main import app
from web_api_server.routers.translate import get_translate_grpc_client


@pytest.fixture
def set_translate_grpc_client() -> Iterator[Callable[[TranslationStub | Mock], None]]:
    """Yield a function that sets the gRPC client the app's routes get; undone after the test."""

    def override_translate_grpc_client(translate_grpc_client: TranslationStub | Mock) -> None:
        app.dependency_overrides[get_translate_grpc_client] = lambda: translate_grpc_client

    yield override_translate_grpc_client
    app.dependency_overrides.clear()


@pytest.fixture
def mock_translate_grpc_client(
    set_translate_grpc_client: Callable[[TranslationStub | Mock], None],
) -> Mock:
    """Replace the gRPC client the routes depend on with a mock whose `Translate` is async."""
    translate_grpc_client_mock = Mock(Translate=AsyncMock())
    set_translate_grpc_client(translate_grpc_client_mock)
    return translate_grpc_client_mock


@pytest.fixture
async def mock_translation_servicer() -> AsyncIterator[Mock]:
    """Serve a mock Translation servicer on an ephemeral port, stored on the mock as `address`.

    `Translate` is created before registering, because the server binds that method then.
    """
    translation_servicer_mock = Mock(Translate=AsyncMock())
    grpc_server = server()
    add_TranslationServicer_to_server(  # type: ignore[no-untyped-call]
        translation_servicer_mock, grpc_server
    )
    grpc_server_ephemeral_port = grpc_server.add_insecure_port(f"{LOOPBACK_IPV4}:0")
    translation_servicer_mock.address = f"{LOOPBACK_IPV4}:{grpc_server_ephemeral_port}"
    await grpc_server.start()
    yield translation_servicer_mock
    await grpc_server.stop(None)
