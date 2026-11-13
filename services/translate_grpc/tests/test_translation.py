from unittest.mock import Mock

import pytest

from translate_grpc.translation import translate_text
from utils.language_name import LanguageName

VALID_LANGUAGE = LanguageName.ITALIAN


def test_translate_text_sends_text_and_language_to_provider(
    mock_translation_provider: Mock,
) -> None:
    mock_translation_provider.request_translation.return_value = "mock translation"

    mock_text = "mock text"
    assert (
        translate_text(
            mock_translation_provider, mock_text, VALID_LANGUAGE, text_length=len(mock_text)
        )
        == "mock translation"
    )
    mock_translation_provider.request_translation.assert_called_once_with(mock_text, VALID_LANGUAGE)


@pytest.mark.parametrize(
    ("text", "raw", "expected"),
    [
        ("hello", ' "ciao"\n', "ciao"),  # quotes and whitespace the model added are dropped
        ('"hello"', '"ciao"', '"ciao"'),  # the input was quoted, so its quotes are kept
        ("hello", "  ciao  ", "ciao"),  # surrounding whitespace is trimmed
    ],
)
def test_translate_text_cleans_provider_output(
    mock_translation_provider: Mock, text: str, raw: str, expected: str
) -> None:
    mock_translation_provider.request_translation.return_value = raw

    assert (
        translate_text(mock_translation_provider, text, VALID_LANGUAGE, text_length=len(text))
        == expected
    )
