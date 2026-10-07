from enum import StrEnum

from translate_proto.translator_pb2 import Language


class LanguageName(StrEnum):
    """Language names deep_translator expects, one per supported proto Language."""

    ENGLISH = "english"
    ITALIAN = "italian"
    SPANISH = "spanish"
    HUNGARIAN = "hungarian"
    POLISH = "polish"
    FRENCH = "french"


def is_supported_language(language: int) -> bool:
    """True if `language` is a proto Language value with a LanguageName member."""
    if language not in Language.values():
        return False
    return Language.Name(language).removeprefix("LANGUAGE_") in LanguageName.__members__


def format_language_name(language: Language) -> LanguageName:
    """LANGUAGE_ITALIAN -> LanguageName.ITALIAN ("italian")."""
    name: str = Language.Name(language)
    return LanguageName[name.removeprefix("LANGUAGE_")]
