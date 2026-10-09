from enum import StrEnum


class LanguageName(StrEnum):
    """Language names deep_translator expects, one per supported proto Language.

    When adding a language here, also add a matching LANGUAGE_<NAME> value to the
    Language enum in protos/translate_proto/translator.proto and regenerate.
    """

    ENGLISH = "english"
    ITALIAN = "italian"
    SPANISH = "spanish"
    HUNGARIAN = "hungarian"
    POLISH = "polish"
    FRENCH = "french"
