from collections.abc import Generator
from contextlib import contextmanager

from opentelemetry.metrics import get_meter

from utils.language_name import LanguageName

# Instruments made before setup_telemetry() installs the meter provider start recording once
# it's installed, so the counter can be created at import time.
translation_counter = get_meter(__name__).create_counter(
    "translations",
    unit="{translation}",
    description="Translations requested from the model, by target language and outcome.",
)


@contextmanager
def count_translation(target_language: LanguageName) -> Generator[None]:
    """Count the translation made inside the with-block, by its target language.

    An error raised in the with-block is counted with its class name as error.type, then
    re-raised, so failed translations can be told apart from completed ones.
    """
    attributes = {"translation.target_language": target_language}
    try:
        yield
    except Exception as error:
        translation_counter.add(1, {**attributes, "error.type": type(error).__qualname__})
        raise
    translation_counter.add(1, attributes)
