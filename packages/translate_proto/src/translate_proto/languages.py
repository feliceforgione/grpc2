from translate_proto.translator_pb2 import Language


def format_language_name(language: Language) -> str:
    """LANGUAGE_ITALIAN -> "italian", the name deep_translator expects."""
    name: str = Language.Name(language)
    return name.removeprefix("LANGUAGE_").lower()
