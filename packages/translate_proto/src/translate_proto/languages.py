from translate_proto.translator_pb2 import Language
from translate_proto.utils import LanguageName


def is_supported_language(language: int) -> bool:
    """True if `language` is a proto Language value with a LanguageName member."""
    if language not in Language.values():
        return False
    return Language.Name(language).removeprefix("LANGUAGE_") in LanguageName.__members__


def convert_language_name(language: Language) -> LanguageName:
    """Convert a proto Language value to its StrEnum LanguageName equivalent.

    LANGUAGE_ITALIAN -> LanguageName.ITALIAN
    """
    name: str = Language.Name(language)
    return LanguageName[name.removeprefix("LANGUAGE_")]
