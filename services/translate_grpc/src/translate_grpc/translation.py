import os
from functools import cache

from deep_translator import ChatGptTranslator
from dotenv import load_dotenv
from opentelemetry.semconv._incubating.attributes.gen_ai_attributes import (
    GEN_AI_OPERATION_NAME,
    GEN_AI_PROVIDER_NAME,
    GEN_AI_REQUEST_MODEL,
    GenAiOperationNameValues,
    GenAiProviderNameValues,
)
from opentelemetry.trace import SpanKind, get_tracer

from utils.language_name import LanguageName

load_dotenv()
apikey = os.environ["OPENAI_API_KEY"]

# deep_translator defaults to gpt-3.5-turbo, which OpenAI has shut down.
OPENAI_MODEL = "gpt-6-luna"

tracer = get_tracer(__name__)


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
    """Translate text with OpenAI, recording the call as a span named per the GenAI conventions.

    deep_translator uses the pre-1.0 openai package, which OpenTelemetry's OpenAI
    instrumentation doesn't support, so the span is recorded here. It holds the text lengths,
    not the text, so users' text stays out of the traces. A raised error marks it as failed.
    """
    with tracer.start_as_current_span(
        f"{GenAiOperationNameValues.CHAT.value} {OPENAI_MODEL}",
        kind=SpanKind.CLIENT,
        attributes={
            GEN_AI_OPERATION_NAME: GenAiOperationNameValues.CHAT.value,
            GEN_AI_PROVIDER_NAME: GenAiProviderNameValues.OPENAI.value,
            GEN_AI_REQUEST_MODEL: OPENAI_MODEL,
            "translation.target_language": target_language,
            "translation.text_length": len(text),
        },
    ) as span:
        translated = _get_translator(target_language).translate(text=text)
        translated = strip_added_quotes(text, translated)
        span.set_attribute("translation.translated_text_length", len(translated))
    return translated


@cache
def _get_translator(target_language: str) -> ChatGptTranslator:
    """Build the translator for a target language once and reuse it on later calls."""
    return ChatGptTranslator(
        api_key=apikey, source=LanguageName.ENGLISH, target=target_language, model=OPENAI_MODEL
    )
