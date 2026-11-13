import logging
from unittest.mock import Mock

import grpc
import grpc.aio
import pytest
from grpc.aio import AioRpcError

from character_count_proto.character_counter_pb2 import (
    CountCharactersRequest,
    CountCharactersResponse,
)
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
    mock_translation_provider: Mock, translate_grpc_channel: grpc.aio.Channel
) -> TranslationStub:
    """Client stub for a server whose translator is mocked.

    Depends on `mock_translation_provider` so the test can set what it returns.
    """
    return TranslationStub(translate_grpc_channel)  # type: ignore[no-untyped-call]


async def test_translate_passes_language_name(
    client: TranslationStub, mock_translation_provider: Mock
) -> None:
    mock_translation_provider.request_translation.return_value = "ciao"
    request = TranslateRequest(text="hello", language=LANGUAGE_ITALIAN)

    response = await client.Translate(request)

    assert response.translated_text == "ciao"
    mock_translation_provider.request_translation.assert_called_once()


@pytest.mark.parametrize("language", [LANGUAGE_UNSPECIFIED, 99])
async def test_missing_or_unknown_language_is_invalid_argument(
    client: TranslationStub, mock_translation_provider: Mock, language: Language
) -> None:
    with pytest.raises(grpc.aio.AioRpcError) as exc_info:
        await client.Translate(TranslateRequest(text="ciao", language=language))

    assert exc_info.value.code() == grpc.StatusCode.INVALID_ARGUMENT
    mock_translation_provider.request_translation.assert_not_called()


async def test_preserves_unicode_text(
    client: TranslationStub, mock_translation_provider: Mock
) -> None:
    text = "¿Szép?👋"
    mock_translation_provider.request_translation.return_value = text

    response = await client.Translate(TranslateRequest(text=text, language=LANGUAGE_HUNGARIAN))

    assert response.translated_text == text


async def test_translator_error_returns_unknown_status(
    client: TranslationStub, mock_translation_provider: Mock
) -> None:
    mock_translation_provider.request_translation.side_effect = RuntimeError("upstream failure")

    with pytest.raises(grpc.aio.AioRpcError) as exc_info:
        await client.Translate(TranslateRequest(text="hello", language=LANGUAGE_ENGLISH))

    assert exc_info.value.code() == grpc.StatusCode.UNKNOWN


async def test_translate_counts_the_text_with_the_character_count_service(
    client: TranslationStub,
    mock_translation_provider: Mock,
    mock_character_count_grpc_client: Mock,
) -> None:
    mock_translation_provider.request_translation.return_value = "ciao"

    await client.Translate(TranslateRequest(text="hello", language=LANGUAGE_ITALIAN))

    mock_character_count_grpc_client.CountCharacters.assert_awaited_once()
    [count_characters_request] = mock_character_count_grpc_client.CountCharacters.await_args.args
    assert count_characters_request == CountCharactersRequest(text_to_count="hello")


@pytest.mark.parametrize(
    "status_code",
    [
        grpc.StatusCode.INVALID_ARGUMENT,  # the text is over the character limit
        grpc.StatusCode.UNAVAILABLE,  # the character count server is down
    ],
)
async def test_failed_count_ends_the_rpc_with_its_status_before_translating(
    client: TranslationStub,
    mock_translation_provider: Mock,
    mock_character_count_grpc_client: Mock,
    status_code: grpc.StatusCode,
) -> None:
    """The caller gets the count's status and details, and the model is never called."""
    mock_character_count_grpc_client.CountCharacters.side_effect = AioRpcError(
        status_code, Mock(), Mock(), details="mock count failure", debug_error_string=None
    )

    with pytest.raises(AioRpcError) as exc_info:
        await client.Translate(TranslateRequest(text="hello", language=LANGUAGE_ITALIAN))

    assert exc_info.value.code() == status_code
    assert exc_info.value.details() == "mock count failure"
    mock_translation_provider.request_translation.assert_not_called()


async def test_translate_logs_lengths_and_language_but_not_the_text(
    client: TranslationStub,
    mock_translation_provider: Mock,
    mock_character_count_grpc_client: Mock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The user's text and its translation stay out of the logs, which are sent to Loki."""
    mock_character_count_grpc_client.CountCharacters.return_value = CountCharactersResponse(
        character_count=22
    )
    mock_translation_provider.request_translation.return_value = "mock translation"
    request = TranslateRequest(text="mock text to translate", language=LANGUAGE_ITALIAN)

    with caplog.at_level(logging.INFO):
        await client.Translate(request)

    [log_message] = [record.getMessage() for record in caplog.records]
    assert log_message == "Translated 22 characters to italian, in 16 characters"
    assert "mock text to translate" not in caplog.text
    assert "mock translation" not in caplog.text
