import os
from functools import cache

from deep_translator import ChatGptTranslator
from dotenv import load_dotenv

from translate_grpc.openai_tracing import trace_openai_translation
from utils.language_name import LanguageName

load_dotenv()
apikey = os.environ["OPENAI_API_KEY"]

# deep_translator defaults to gpt-3.5-turbo, which OpenAI has shut down.
OPENAI_MODEL = "gpt-6-luna"


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
    """Translate text into the target language with OpenAI."""
    chat_gpt_answer = _ask_chat_gpt_to_translate(text, target_language)
    return strip_added_quotes(text, chat_gpt_answer)


def _ask_chat_gpt_to_translate(text: str, target_language: LanguageName) -> str:
    """Send text to ChatGPT for translation and return its answer as is."""
    with trace_openai_translation(OPENAI_MODEL, text, target_language) as trace:
        # deep_translator has no type hints, so its result is annotated here.
        chat_gpt_answer: str = _get_translator(target_language).translate(text=text)
        trace.record_answer(chat_gpt_answer)
    return chat_gpt_answer


@cache
def _get_translator(target_language: str) -> ChatGptTranslator:
    """Build the translator for a target language once and reuse it on later calls."""
    return ChatGptTranslator(
        api_key=apikey, source=LanguageName.ENGLISH, target=target_language, model=OPENAI_MODEL
    )
