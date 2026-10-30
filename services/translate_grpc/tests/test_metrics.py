from collections.abc import Callable
from unittest.mock import Mock

import pytest
from opentelemetry.sdk.metrics.export import Metric, NumberDataPoint

from translate_grpc.translation import translate_text
from utils.language_name import LanguageName

TRANSLATIONS_METRIC_NAME = "translations"
VALID_TEXT = "hello"
VALID_LANGUAGE = LanguageName.ITALIAN


def get_translation_counts(metrics_by_name: dict[str, Metric]) -> list[NumberDataPoint]:
    """Return the translation counter's data points, one per set of attributes."""
    translations_metric = metrics_by_name[TRANSLATIONS_METRIC_NAME]
    return list(translations_metric.data.data_points)  # type: ignore[arg-type]


def test_translation_is_counted_by_target_language(
    mock_chat_gpt_translator_translate: Mock,
    get_recorded_metrics_by_name: Callable[[], dict[str, Metric]],
) -> None:
    """Each language gets its own count, so the dashboard can compare them."""
    mock_chat_gpt_translator_translate.return_value = "mock"

    translate_text(VALID_TEXT, VALID_LANGUAGE)
    translate_text(VALID_TEXT, VALID_LANGUAGE)
    translate_text(VALID_TEXT, LanguageName.SPANISH)

    translation_counts = get_translation_counts(get_recorded_metrics_by_name())
    counts_by_attributes = {
        tuple(sorted((translation_count.attributes or {}).items())): translation_count.value
        for translation_count in translation_counts
    }
    assert counts_by_attributes == {
        (("translation.target_language", VALID_LANGUAGE),): 2,
        (("translation.target_language", LanguageName.SPANISH),): 1,
    }


def test_failed_translation_is_counted_with_its_error_type(
    mock_chat_gpt_translator_translate: Mock,
    get_recorded_metrics_by_name: Callable[[], dict[str, Metric]],
) -> None:
    """A failed call to the model is counted, with error.type, and the error still raised."""
    mock_chat_gpt_translator_translate.side_effect = RuntimeError("upstream failure")

    with pytest.raises(RuntimeError):
        translate_text(VALID_TEXT, VALID_LANGUAGE)

    [translation_count] = get_translation_counts(get_recorded_metrics_by_name())
    assert translation_count.value == 1
    assert translation_count.attributes == {
        "translation.target_language": VALID_LANGUAGE,
        "error.type": "RuntimeError",
    }
