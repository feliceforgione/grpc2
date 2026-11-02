from collections.abc import Iterator
from unittest.mock import Mock, patch

import pytest

from translate_grpc.deep_translator_provider import DeepTranslatorProvider
from utils.language_name import LanguageName

VALID_API_KEY = "test-key"
VALID_LANGUAGE = LanguageName.ITALIAN


@pytest.fixture
def mock_chat_gpt_translator() -> Iterator[Mock]:
    """Replace deep_translator's ChatGptTranslator, so no test calls OpenAI."""
    with patch(
        "translate_grpc.deep_translator_provider.ChatGptTranslator"
    ) as mock_chat_gpt_translator:
        yield mock_chat_gpt_translator


@pytest.fixture
def deep_translator_provider(mock_chat_gpt_translator: Mock) -> DeepTranslatorProvider:
    """A provider whose ChatGptTranslator is the mock."""
    return DeepTranslatorProvider(VALID_API_KEY)


def test_request_translation_returns_the_translators_answer(
    mock_chat_gpt_translator: Mock, deep_translator_provider: DeepTranslatorProvider
) -> None:
    mock_chat_gpt_translator.return_value.translate.return_value = ' "ciao"\n'

    raw_translation = deep_translator_provider.request_translation("hello", VALID_LANGUAGE)

    # Returned as is; translate_text does the clean-up.
    assert raw_translation == ' "ciao"\n'
    mock_chat_gpt_translator.return_value.translate.assert_called_once_with(text="hello")


def test_translator_is_built_with_key_language_and_supported_model(
    mock_chat_gpt_translator: Mock, deep_translator_provider: DeepTranslatorProvider
) -> None:
    deep_translator_provider.request_translation("hello", VALID_LANGUAGE)

    mock_chat_gpt_translator.assert_called_once_with(
        api_key=VALID_API_KEY,
        source=LanguageName.ENGLISH,
        target=VALID_LANGUAGE,
        model=deep_translator_provider.model,
    )
    assert deep_translator_provider.model == "gpt-6-luna"


def test_translator_is_built_once_per_language(
    mock_chat_gpt_translator: Mock, deep_translator_provider: DeepTranslatorProvider
) -> None:
    deep_translator_provider.request_translation("hello", VALID_LANGUAGE)
    deep_translator_provider.request_translation("goodbye", VALID_LANGUAGE)
    deep_translator_provider.request_translation("hello", LanguageName.SPANISH)

    targets = [call.kwargs["target"] for call in mock_chat_gpt_translator.call_args_list]
    assert targets == [VALID_LANGUAGE, LanguageName.SPANISH]
