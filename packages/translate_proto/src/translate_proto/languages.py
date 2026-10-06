from translate_proto import translator_pb2


def language_name(language: translator_pb2.Language) -> str:
    """LANGUAGE_ITALIAN -> "italian", the name deep_translator expects."""
    return translator_pb2.Language.Name(language).removeprefix("LANGUAGE_").lower()
