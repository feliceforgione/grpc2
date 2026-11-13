from opentelemetry.metrics import get_meter

# The error.type of a text rejected for having more than MAX_CHARACTER_COUNT characters.
TEXT_TOO_LONG_ERROR_TYPE = "text_too_long"

# Instruments made before setup_telemetry() installs the meter provider start recording once
# it's installed, so the histogram can be created at import time.
# The default boundaries (0, 5, 10, 25, 50, ...) are too coarse for texts capped at 15
# characters, so these are finer below the cap, with a few above it for rejected texts.
text_length_histogram = get_meter(__name__).create_histogram(
    "character_count.text.length",
    unit="{character}",
    description="Characters in the texts sent to be counted, by outcome.",
    explicit_bucket_boundaries_advisory=[0, 1, 3, 5, 7, 9, 11, 13, 15, 20, 50, 100, 1000],
)


def record_text_length(character_count: int, error_type: str | None = None) -> None:
    """Record the length of a text sent to be counted.

    A rejected text is recorded with error.type, so rejected requests can be told apart
    from counted ones. Each recording is also one request in the histogram's count.
    """
    attributes = {} if error_type is None else {"error.type": error_type}
    text_length_histogram.record(character_count, attributes)
