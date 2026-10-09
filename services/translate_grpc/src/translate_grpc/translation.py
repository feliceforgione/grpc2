import os
from functools import cache

from deep_translator import ChatGptTranslator
from dotenv import load_dotenv

from translate_proto.utils import LanguageName

load_dotenv()
apikey = os.environ["OPENAI_API_KEY"]


def strip_added_quotes(text: str, translated: str) -> str:
    """Trim whitespace and drop quotes ChatGPT wrapped around its answer.

    Quotes are kept when the input text was quoted too.

    >>> strip_added_quotes("Hello", ' "Ciao"\\n')
    'Ciao'
    >>> strip_added_quotes('"Hello"', '"Ciao"')
    '"Ciao"'
    """
    translated = translated.strip()
    if (
        not text.strip().startswith('"')
        and len(translated) >= 2
        and translated[0] == translated[-1] == '"'
    ):
        return translated[1:-1]
    return translated


def translate_text(text: str, target_language: LanguageName = LanguageName.ENGLISH) -> str:
    translated = _get_translator(target_language).translate(text=text)
    return strip_added_quotes(text, translated)


@cache
def _get_translator(target_language: str) -> ChatGptTranslator:
    """Build the translator for a target language once and reuse it on later calls."""
    return ChatGptTranslator(api_key=apikey, source=LanguageName.ENGLISH, target=target_language)
