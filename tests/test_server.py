from unittest.mock import Mock

import grpc
import pytest

from translate_grpc import server
from translate_proto.translator_pb2 import (
    LANGUAGE_ENGLISH,
    LANGUAGE_HUNGARIAN,
    LANGUAGE_ITALIAN,
    LANGUAGE_UNSPECIFIED,
    Language,
    TranslateRequest,
)
from translate_proto.translator_pb2_grpc import TranslationStub


@pytest.fixture
def calls(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str]]:
    """Replace the OpenAI-backed translator with a fake and record its calls."""
    recorded: list[tuple[str, str]] = []

    def fake_translate_text(text: str, language: str = "english") -> str:
        recorded.append((text, language))
        return f"[{language}] {text}"

    monkeypatch.setattr(server, "translate_text", fake_translate_text)
    return recorded


@pytest.fixture
async def stub(calls: list[tuple[str, str]], channel: grpc.aio.Channel) -> TranslationStub:
    """Client stub for a server whose translator is faked (depends on `calls` to patch first)."""
    return TranslationStub(channel)  # type: ignore[no-untyped-call]


async def test_translate_passes_language_name(
    stub: TranslationStub, calls: list[tuple[str, str]]
) -> None:
    request = TranslateRequest(text="hello", language=LANGUAGE_ITALIAN)

    response = await stub.Translate(request)

    assert response.translated_text == "[italian] hello"
    assert calls == [("hello", "italian")]


@pytest.mark.parametrize("language", [LANGUAGE_UNSPECIFIED, 99])
async def test_missing_or_unknown_language_is_invalid_argument(
    stub: TranslationStub, calls: list[tuple[str, str]], language: Language
) -> None:
    with pytest.raises(grpc.aio.AioRpcError) as exc_info:
        await stub.Translate(TranslateRequest(text="ciao", language=language))

    assert exc_info.value.code() == grpc.StatusCode.INVALID_ARGUMENT
    assert calls == []


async def test_preserves_unicode_text(stub: TranslationStub) -> None:
    text = "¿Szép?👋"

    response = await stub.Translate(
        TranslateRequest(text=text, language=LANGUAGE_HUNGARIAN)
    )

    assert response.translated_text == f"[hungarian] {text}"


async def test_translator_error_returns_unknown_status(
    stub: TranslationStub, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        server, "translate_text", Mock(side_effect=RuntimeError("upstream failure"))
    )

    with pytest.raises(grpc.aio.AioRpcError) as exc_info:
        await stub.Translate(
            TranslateRequest(text="hello", language=LANGUAGE_ENGLISH)
        )

    assert exc_info.value.code() == grpc.StatusCode.UNKNOWN
