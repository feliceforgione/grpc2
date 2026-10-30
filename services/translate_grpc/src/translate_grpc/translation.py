import os
from functools import cache

from deep_translator import ChatGptTranslator
from dotenv import load_dotenv

from translate_grpc.translation_metrics import count_translation
from translate_grpc.translation_tracing import trace_translation
from utils.language_name import LanguageName

load_dotenv()
apikey = os.environ["OPENAI_API_KEY"]

# deep_translator defaults to gpt-3.5-turbo, which OpenAI has shut down.
TRANSLATION_MODEL = "gpt-6-luna"
TRANSLATION_PROVIDER = "openai"


def strip_added_quotes(text: str, translated: str) -> str:
    """Trim whitespace and drop quotes the model wrapped around its answer.

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
    """Translate text into the target language."""
    with count_translation(target_language):
        raw_translation = _request_translation(text, target_language)
    return strip_added_quotes(text, raw_translation)


def _request_translation(text: str, target_language: LanguageName) -> str:
    """Send text to the model for translation and return its answer as is."""
    # deep_translator uses the pre-1.0 openai package, which OpenTelemetry's OpenAI
    # instrumentation doesn't support, so the call is traced by hand.
    with trace_translation(TRANSLATION_PROVIDER, TRANSLATION_MODEL, text, target_language) as trace:
        # deep_translator has no type hints, so its result is annotated here.
        raw_translation: str = _get_translator(target_language).translate(text=text)
        trace.record_answer(raw_translation)
    return raw_translation


@cache
def _get_translator(target_language: str) -> ChatGptTranslator:
    """Build the translator for a target language once and reuse it on later calls."""
    return ChatGptTranslator(
        api_key=apikey, source=LanguageName.ENGLISH, target=target_language, model=TRANSLATION_MODEL
    )
