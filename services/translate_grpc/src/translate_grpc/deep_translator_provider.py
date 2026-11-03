"""The translation provider that calls OpenAI through deep_translator's ChatGptTranslator."""

from typing import ClassVar

from deep_translator import ChatGptTranslator

from utils.language_name import LanguageName


class DeepTranslatorProvider:
    """Translate with OpenAI through deep_translator, building one translator per language."""

    PROVIDER_NAME: ClassVar[str] = "openai"
    # deep_translator defaults to gpt-3.5-turbo, which OpenAI has shut down.
    MODEL: ClassVar[str] = "gpt-6-luna"

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._language_translators: dict[LanguageName, ChatGptTranslator] = {}

    def request_translation(self, text: str, target_language: LanguageName) -> str:
        """Send text to the model for translation and return its answer as is."""
        # deep_translator has no type hints, so its result is annotated here.
        translation: str = self._get_translator(target_language).translate(text=text)
        return translation

    def _get_translator(self, target_language: LanguageName) -> ChatGptTranslator:
        """Build the translator for a target language once and reuse it on later calls."""
        if target_language not in self._language_translators:
            self._language_translators[target_language] = ChatGptTranslator(
                api_key=self._api_key,
                source=LanguageName.ENGLISH,
                target=target_language,
                model=self.MODEL,
            )
        return self._language_translators[target_language]
