from translate_grpc.translation_metrics import count_translation
from translate_grpc.translation_provider import TranslationProvider
from translate_grpc.translation_tracing import trace_translation
from utils.language_name import LanguageName


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


def translate_text(
    translation_provider: TranslationProvider,
    text: str,
    target_language: LanguageName = LanguageName.ENGLISH,
) -> str:
    """Translate text into the target language with the given provider."""
    with count_translation(target_language):
        translation = _request_translation(translation_provider, text, target_language)
    return strip_added_quotes(text, translation)


def _request_translation(
    translation_provider: TranslationProvider, text: str, target_language: LanguageName
) -> str:
    """Ask the provider for a translation inside a span, and return its answer as is."""
    # The provider calls aren't traced by an instrumentation library (deep_translator uses
    # the pre-1.0 openai package, which OpenTelemetry's OpenAI instrumentation doesn't
    # support), so the call is traced by hand.
    with trace_translation(
        translation_provider.PROVIDER_NAME, translation_provider.MODEL, text, target_language
    ) as trace:
        translation = translation_provider.request_translation(text, target_language)
        trace.record_answer(translation)
    return translation
