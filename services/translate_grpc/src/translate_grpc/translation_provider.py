"""The interface translate_text uses to ask a model for a translation."""

from typing import ClassVar, Protocol

from utils.language_name import LanguageName


class TranslationProvider(Protocol):
    """A model that translates text, which the server is given when it starts.

    Only the call to the model goes here. translate_text adds the metrics, the span and the
    clean-up around it, so every provider gets them without repeating them.
    """

    # Recorded on the span as gen_ai.provider.name and gen_ai.request.model.
    PROVIDER_NAME: ClassVar[str]
    MODEL: ClassVar[str]

    def request_translation(self, text: str, target_language: LanguageName) -> str:
        """Send text to the model for translation and return its answer as is."""
        ...
