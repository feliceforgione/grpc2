from opentelemetry.metrics import get_meter

# Instruments made before setup_telemetry() installs the meter provider start recording once
# it's installed, so the histogram can be created at import time.
# The default boundaries (0, 5, 10, 25, 50, ...) are too coarse for texts capped at 15
# characters, so these are finer below the cap, with a few above it for rejected texts.
text_length_histogram = get_meter(__name__).create_histogram(
    "character_count.text.length",
    unit="{character}",
    description="Characters in the texts sent to be counted, by whether they were over the limit.",
    explicit_bucket_boundaries_advisory=[0, 1, 3, 5, 7, 9, 11, 13, 15, 20, 50, 100, 1000],
)


def record_text_length(character_count: int, is_over_limit: bool) -> None:
    """Record the length of a text sent to be counted.

    is_over_limit records whether the text was over the limit when it was sent, so the history
    stays right if the limit changes. Each recording is also one request in the histogram's
    count.
    """
    text_length_histogram.record(character_count, {"is_over_limit": is_over_limit})
