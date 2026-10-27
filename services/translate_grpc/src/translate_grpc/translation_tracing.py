from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass

from opentelemetry.trace import Span, SpanKind, get_tracer

from utils.language_name import LanguageName


@dataclass(frozen=True)
class TranslationTrace:
    """The open span of one translation call, for recording what the call returned."""

    _span: Span

    def record_answer(self, answer: str) -> None:
        """Record the length of the provider's answer, as sent, before any clean-up."""
        self._span.set_attribute("translation.answer_length", len(answer))


@contextmanager
def trace_translation(
    provider: str, model: str, text: str, target_language: LanguageName
) -> Generator[TranslationTrace]:
    """Record the model call made inside the with-block as a span named per the GenAI conventions.

    The span holds the text lengths, not the text, so users' text stays out of the traces.
    An error raised in the with-block marks it as failed.

    The gen_ai.* names are written out because opentelemetry-semantic-conventions deprecated
    its constants for them when the GenAI conventions moved to their own repository
    (open-telemetry/semantic-conventions-genai), which has no Python package yet.
    """
    tracer = get_tracer(__name__)
    with tracer.start_as_current_span(
        f"chat {model}",
        kind=SpanKind.CLIENT,
        attributes={
            "gen_ai.operation.name": "chat",
            "gen_ai.provider.name": provider,
            "gen_ai.request.model": model,
            "translation.target_language": target_language,
            "translation.text_length": len(text),
        },
    ) as span:
        yield TranslationTrace(span)
