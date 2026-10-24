from collections.abc import Iterator
from unittest.mock import Mock, patch

import pytest
from deep_translator import ChatGptTranslator

from translate_grpc.translation import OPENAI_MODEL, _get_translator, translate_text
from utils.language_name import LanguageName


@pytest.fixture
def chatgpt_translate() -> Iterator[Mock]:
    """Replace ChatGptTranslator.translate (the OpenAI call); tests set its return_value."""
    with patch.object(ChatGptTranslator, "translate") as mock:
        yield mock


def test_translate_text_sends_text_to_translator(chatgpt_translate: Mock) -> None:
    chatgpt_translate.return_value = "ciao"

    assert translate_text("hello", LanguageName.ITALIAN) == "ciao"
    chatgpt_translate.assert_called_once_with(text="hello")


def test_translate_text_uses_supported_openai_model() -> None:
    # Translators are cached per language, so clear the cache to build a new one,
    # and again afterwards so later tests don't get the mock.
    _get_translator.cache_clear()
    try:
        with patch("translate_grpc.translation.ChatGptTranslator") as mock_chat_gpt_translator:
            mock_chat_gpt_translator.return_value.translate.return_value = "ciao"

            translate_text("hello", LanguageName.ITALIAN)
    finally:
        _get_translator.cache_clear()

    assert mock_chat_gpt_translator.call_args.kwargs["model"] == OPENAI_MODEL


@pytest.mark.parametrize(
    ("text", "raw", "expected"),
    [
        ("hello", ' "ciao"\n', "ciao"),
        ('"hello"', '"ciao"', '"ciao"'),
        ("hello", "  ciao  ", "ciao"),
    ],
)
def test_translate_text_cleans_translator_output(
    chatgpt_translate: Mock, text: str, raw: str, expected: str
) -> None:
    chatgpt_translate.return_value = raw

    assert translate_text(text, LanguageName.ITALIAN) == expected
