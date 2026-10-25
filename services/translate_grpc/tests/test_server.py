from unittest.mock import Mock

import grpc
import grpc.aio
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
async def client(
    mock_chat_gpt_translator_translate: Mock, translate_grpc_channel: grpc.aio.Channel
) -> TranslationStub:
    """Client stub for a server whose translator is mocked.

    Depends on `mock_chat_gpt_translator_translate` so the patch is in place first.
    """
    return TranslationStub(translate_grpc_channel)  # type: ignore[no-untyped-call]


async def test_translate_passes_language_name(
    client: TranslationStub, mock_chat_gpt_translator_translate: Mock
) -> None:
    mock_chat_gpt_translator_translate.return_value = "ciao"
    request = TranslateRequest(text="hello", language=LANGUAGE_ITALIAN)

    response = await client.Translate(request)

    assert response.translated_text == "ciao"
    mock_chat_gpt_translator_translate.assert_called_once()


@pytest.mark.parametrize("language", [LANGUAGE_UNSPECIFIED, 99])
async def test_missing_or_unknown_language_is_invalid_argument(
    client: TranslationStub, mock_chat_gpt_translator_translate: Mock, language: Language
) -> None:
    with pytest.raises(grpc.aio.AioRpcError) as exc_info:
        await client.Translate(TranslateRequest(text="ciao", language=language))

    assert exc_info.value.code() == grpc.StatusCode.INVALID_ARGUMENT
    mock_chat_gpt_translator_translate.assert_not_called()


async def test_preserves_unicode_text(
    client: TranslationStub, mock_chat_gpt_translator_translate: Mock
) -> None:
    text = "¿Szép?👋"
    mock_chat_gpt_translator_translate.return_value = text

    response = await client.Translate(TranslateRequest(text=text, language=LANGUAGE_HUNGARIAN))

    assert response.translated_text == text


async def test_translator_error_returns_unknown_status(
    client: TranslationStub, mock_chat_gpt_translator_translate: Mock
) -> None:
    mock_chat_gpt_translator_translate.side_effect = RuntimeError("upstream failure")

    with pytest.raises(grpc.aio.AioRpcError) as exc_info:
        await client.Translate(TranslateRequest(text="hello", language=LANGUAGE_ENGLISH))

    assert exc_info.value.code() == grpc.StatusCode.UNKNOWN
