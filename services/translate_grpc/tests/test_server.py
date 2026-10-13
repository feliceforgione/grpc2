from collections.abc import Iterator
from unittest.mock import Mock, patch

import grpc
import grpc.aio
import pytest
from deep_translator import ChatGptTranslator

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
def translate() -> Iterator[Mock]:
    """Mock `ChatGptTranslator.translate` so the real translator is built but never calls OpenAI.

    autospec=True keeps the method signature, so each call receives the translator
    instance as its first argument;
    """
    with patch.object(ChatGptTranslator, "translate", autospec=True) as mock:
        yield mock


@pytest.fixture
async def client(translate: Mock, channel: grpc.aio.Channel) -> TranslationStub:
    """Client stub for a server whose translator is mocked.

    Depends on `translate` so the patch is in place first.
    """
    return TranslationStub(channel)  # type: ignore[no-untyped-call]


async def test_translate_passes_language_name(client: TranslationStub, translate: Mock) -> None:
    translate.return_value = "ciao"
    request = TranslateRequest(text="hello", language=LANGUAGE_ITALIAN)

    response = await client.Translate(request)

    assert response.translated_text == "ciao"
    translate.assert_called_once()


@pytest.mark.parametrize("language", [LANGUAGE_UNSPECIFIED, 99])
async def test_missing_or_unknown_language_is_invalid_argument(
    client: TranslationStub, translate: Mock, language: Language
) -> None:
    with pytest.raises(grpc.aio.AioRpcError) as exc_info:
        await client.Translate(TranslateRequest(text="ciao", language=language))

    assert exc_info.value.code() == grpc.StatusCode.INVALID_ARGUMENT
    translate.assert_not_called()


async def test_preserves_unicode_text(client: TranslationStub, translate: Mock) -> None:
    text = "¿Szép?👋"
    translate.side_effect = lambda _, text: text

    response = await client.Translate(TranslateRequest(text=text, language=LANGUAGE_HUNGARIAN))

    assert response.translated_text == text


async def test_translator_error_returns_unknown_status(
    client: TranslationStub, translate: Mock
) -> None:
    translate.side_effect = RuntimeError("upstream failure")

    with pytest.raises(grpc.aio.AioRpcError) as exc_info:
        await client.Translate(TranslateRequest(text="hello", language=LANGUAGE_ENGLISH))

    assert exc_info.value.code() == grpc.StatusCode.UNKNOWN
