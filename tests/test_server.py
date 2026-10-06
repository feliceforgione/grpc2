import os
import string
from contextlib import asynccontextmanager

import grpc
import pytest

from translate_grpc import server
from translate_proto import translator_pb2, translator_pb2_grpc


@pytest.fixture
def calls(monkeypatch):
    """Replace the OpenAI-backed translator with a fake and record its calls."""
    recorded = []

    def fake_translate_text(text: str, language: str = "english") -> str:
        recorded.append((text, language))
        return f"[{language}] {text}"

    monkeypatch.setattr(server, "translate_text", fake_translate_text)
    return recorded


@asynccontextmanager
async def running_server():
    """Run the real Translator servicer on an ephemeral port and yield a client stub."""
    grpc_server = grpc.aio.server()
    translator_pb2_grpc.add_TranslationServicer_to_server(server.Translator(), grpc_server)
    port = grpc_server.add_insecure_port("127.0.0.1:0")
    await grpc_server.start()
    try:
        async with grpc.aio.insecure_channel(f"127.0.0.1:{port}") as channel:
            yield channel
    finally:
        await grpc_server.stop(None)


@pytest.fixture
async def stub(calls):
    """Client stub for a server whose translator is faked (depends on `calls` to patch first)."""
    async with running_server() as channel:
        yield translator_pb2_grpc.TranslationStub(channel)


@pytest.mark.parametrize(
    ("value", "name"),
    [
        (translator_pb2.LANGUAGE_ENGLISH, "english"),
        (translator_pb2.LANGUAGE_ITALIAN, "italian"),
        (translator_pb2.LANGUAGE_SPANISH, "spanish"),
        (translator_pb2.LANGUAGE_HUNGARIAN, "hungarian"),
        (translator_pb2.LANGUAGE_POLISH, "polish"),
        (translator_pb2.LANGUAGE_FRENCH, "french"),
    ],
)
async def test_translate_passes_language_name(stub, calls, value, name):
    request = translator_pb2.TranslateRequest(text="hello", language=value)

    response = await stub.Translate(request)

    assert response.translated_text == f"[{name}] hello"
    assert calls == [("hello", name)]


@pytest.mark.parametrize("language", [translator_pb2.LANGUAGE_UNSPECIFIED, 99])
async def test_missing_or_unknown_language_is_invalid_argument(stub, calls, language):
    with pytest.raises(grpc.aio.AioRpcError) as exc_info:
        await stub.Translate(translator_pb2.TranslateRequest(text="ciao", language=language))

    assert exc_info.value.code() == grpc.StatusCode.INVALID_ARGUMENT
    assert calls == []


async def test_preserves_unicode_text(stub, calls):
    text = "¿Szép?👋"

    response = await stub.Translate(
        translator_pb2.TranslateRequest(text=text, language=translator_pb2.LANGUAGE_HUNGARIAN)
    )

    assert response.translated_text == f"[hungarian] {text}"


async def test_translator_error_returns_unknown_status(stub, monkeypatch):
    def boom(text: str, language: str = "english") -> str:
        raise RuntimeError("upstream failure")

    monkeypatch.setattr(server, "translate_text", boom)

    with pytest.raises(grpc.aio.AioRpcError) as exc_info:
        await stub.Translate(
            translator_pb2.TranslateRequest(text="hello", language=translator_pb2.LANGUAGE_ENGLISH)
        )

    assert exc_info.value.code() == grpc.StatusCode.UNKNOWN


@pytest.mark.live
@pytest.mark.skipif(
    os.environ["OPENAI_API_KEY"] == "test-key", reason="OPENAI_API_KEY not configured"
)
async def test_live_translate_hello_to_italian():
    async with running_server() as channel:
        response = await translator_pb2_grpc.TranslationStub(channel).Translate(
            translator_pb2.TranslateRequest(text="Hello", language=translator_pb2.LANGUAGE_ITALIAN)
        )

    # The model may add punctuation or capitalisation ("Ciao!"), so normalise first.
    assert response.translated_text.strip(string.punctuation + " ").casefold() == "ciao"
