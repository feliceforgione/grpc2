import os
from functools import cache

from deep_translator import ChatGptTranslator
from dotenv import load_dotenv
from translate_proto.languages import format_language_name
from translate_proto.translator_pb2 import LANGUAGE_ENGLISH

load_dotenv()
apikey = os.environ["OPENAI_API_KEY"]
ENGLISH = format_language_name(LANGUAGE_ENGLISH)


def strip_added_quotes(text: str, translated: str) -> str:
    """Drop quotes ChatGPT wrapped around its answer, unless the input was quoted too.

    >>> strip_added_quotes("Hello", '"Ciao"')
    'Ciao'
    >>> strip_added_quotes('"Hello"', '"Ciao"')
    '"Ciao"'
    """
    if not text.strip().startswith('"') and len(translated) >= 2 and translated[0] == translated[-1] == '"':
        return translated[1:-1]
    return translated


@cache
def _get_translator(target: str) -> ChatGptTranslator:
    """Build the translator for a target language once and reuse it on later calls."""
    return ChatGptTranslator(api_key=apikey, source=ENGLISH, target=target)


def translate_text(text: str, language: str = ENGLISH) -> str:
    translated = _get_translator(language).translate(text=text).strip()
    return strip_added_quotes(text, translated)
