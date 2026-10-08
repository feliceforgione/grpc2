from collections.abc import Iterator
from unittest.mock import Mock, patch

import pytest
from deep_translator import ChatGptTranslator

from translate_grpc.translation import translate_text
from translate_proto.utils import LanguageName


@pytest.fixture
def chatgpt_translate() -> Iterator[Mock]:
    """Replace ChatGptTranslator.translate (the OpenAI call); tests set its return_value."""
    with patch.object(ChatGptTranslator, "translate") as mock:
        yield mock


def test_translate_text_sends_text_to_translator(chatgpt_translate: Mock) -> None:
    chatgpt_translate.return_value = "ciao"

    assert translate_text("hello", LanguageName.ITALIAN) == "ciao"
    chatgpt_translate.assert_called_once_with(text="hello")


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
