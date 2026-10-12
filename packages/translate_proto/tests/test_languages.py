import pytest

from translate_proto.languages import (
    convert_language_name,
    convert_to_proto_language,
    is_supported_language,
)
from translate_proto.translator_pb2 import (
    LANGUAGE_ENGLISH,
    LANGUAGE_FRENCH,
    LANGUAGE_HUNGARIAN,
    LANGUAGE_ITALIAN,
    LANGUAGE_POLISH,
    LANGUAGE_SPANISH,
    LANGUAGE_UNSPECIFIED,
    Language,
)
from translate_proto.utils import LanguageName

SUPPORTED_LANGUAGE = [value for value in Language.values() if value != LANGUAGE_UNSPECIFIED]


@pytest.mark.parametrize("language", SUPPORTED_LANGUAGE, ids=Language.Name)
def test_every_proto_language_has_a_language_name(language: Language) -> None:
    """Fails when a Language is added to the proto without a matching LanguageName member."""
    assert isinstance(convert_language_name(language), LanguageName)
    assert is_supported_language(language)


@pytest.mark.parametrize("name", LanguageName, ids=lambda name: name.name)
def test_every_language_name_has_a_proto_language(name: LanguageName) -> None:
    """Fails when a LanguageName member is added without a matching Language in the proto."""
    assert f"LANGUAGE_{name.name}" in Language.keys()


@pytest.mark.parametrize(
    ("language", "name"),
    [
        (LANGUAGE_ENGLISH, "english"),
        (LANGUAGE_ITALIAN, "italian"),
        (LANGUAGE_SPANISH, "spanish"),
        (LANGUAGE_HUNGARIAN, "hungarian"),
        (LANGUAGE_POLISH, "polish"),
        (LANGUAGE_FRENCH, "french"),
    ],
)
def test_convert_language_name(language: Language, name: str) -> None:
    assert convert_language_name(language) == name


@pytest.mark.parametrize(
    ("name", "language"),
    [
        (LanguageName.ENGLISH, LANGUAGE_ENGLISH),
        (LanguageName.ITALIAN, LANGUAGE_ITALIAN),
        (LanguageName.SPANISH, LANGUAGE_SPANISH),
        (LanguageName.HUNGARIAN, LANGUAGE_HUNGARIAN),
        (LanguageName.POLISH, LANGUAGE_POLISH),
        (LanguageName.FRENCH, LANGUAGE_FRENCH),
    ],
)
def test_convert_to_proto_language(name: LanguageName, language: Language) -> None:
    assert convert_to_proto_language(name) == language


@pytest.mark.parametrize("language", [LANGUAGE_UNSPECIFIED, 99])
def test_unspecified_or_unknown_language_is_not_supported(language: int) -> None:
    assert not is_supported_language(language)
