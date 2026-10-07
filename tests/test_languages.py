import pytest

from translate_proto.languages import LanguageName, format_language_name, is_supported_language
from translate_proto.translator_pb2 import LANGUAGE_UNSPECIFIED, Language

SUPPORTED = [value for value in Language.values() if value != LANGUAGE_UNSPECIFIED]


@pytest.mark.parametrize("language", SUPPORTED, ids=Language.Name)
def test_every_proto_language_has_a_language_name(language: Language) -> None:
    """Fails when a Language is added to the proto without a matching LanguageName member."""
    assert isinstance(format_language_name(language), LanguageName)
    assert is_supported_language(language)


@pytest.mark.parametrize("language", [LANGUAGE_UNSPECIFIED, 99])
def test_unspecified_or_unknown_language_is_not_supported(language: int) -> None:
    assert not is_supported_language(language)
