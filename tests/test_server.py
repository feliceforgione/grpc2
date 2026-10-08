from collections.abc import Iterator
from unittest.mock import Mock, patch

import grpc
import pytest

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
def translate_text() -> Iterator[Mock]:
    """Replace the OpenAI-backed translator with a mock that echoes its input."""
    with patch(
        "translate_grpc.server.translate_text",
        side_effect=lambda text, language: f"[{language}] {text}",
    ) as mock:
        yield mock


@pytest.fixture
async def stub(translate_text: Mock, channel: grpc.aio.Channel) -> TranslationStub:
    """Client stub for a server whose translator is mocked (depends on `translate_text` to patch first)."""
    return TranslationStub(channel)  


async def test_translate_passes_language_name(
    stub: TranslationStub, translate_text: Mock
) -> None:
    request = TranslateRequest(text="hello", language=LANGUAGE_ITALIAN)

    response = await stub.Translate(request)

    assert response.translated_text == "[italian] hello"
    translate_text.assert_called_once_with("hello", "italian")


@pytest.mark.parametrize("language", [LANGUAGE_UNSPECIFIED, 99])
async def test_missing_or_unknown_language_is_invalid_argument(
    stub: TranslationStub, translate_text: Mock, language: Language
) -> None:
    with pytest.raises(grpc.aio.AioRpcError) as exc_info:
        await stub.Translate(TranslateRequest(text="ciao", language=language))

    assert exc_info.value.code() == grpc.StatusCode.INVALID_ARGUMENT
    translate_text.assert_not_called()


async def test_preserves_unicode_text(stub: TranslationStub) -> None:
    text = "¿Szép?👋"

    response = await stub.Translate(
        TranslateRequest(text=text, language=LANGUAGE_HUNGARIAN)
    )

    assert response.translated_text == f"[hungarian] {text}"


async def test_translator_error_returns_unknown_status(
    stub: TranslationStub, translate_text: Mock
) -> None:
    translate_text.side_effect = RuntimeError("upstream failure")

    with pytest.raises(grpc.aio.AioRpcError) as exc_info:
        await stub.Translate(
            TranslateRequest(text="hello", language=LANGUAGE_ENGLISH)
        )

    assert exc_info.value.code() == grpc.StatusCode.UNKNOWN
