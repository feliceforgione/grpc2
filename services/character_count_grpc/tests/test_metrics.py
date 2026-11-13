from collections.abc import Callable

import pytest
from grpc.aio import AioRpcError
from opentelemetry.sdk.metrics.export import HistogramDataPoint, Metric

from character_count_grpc.character_count_metrics import TEXT_TOO_LONG_ERROR_TYPE
from character_count_grpc.character_counter_servicer import MAX_CHARACTER_COUNT
from character_count_proto.character_counter_pb2 import CountCharactersRequest
from character_count_proto.character_counter_pb2_grpc import CharacterCounterStub

TEXT_LENGTH_METRIC_NAME = "character_count.text.length"


def get_text_lengths(metrics_by_name: dict[str, Metric]) -> list[HistogramDataPoint]:
    """Return the text length histogram's data points, one per set of attributes."""
    text_length_metric = metrics_by_name[TEXT_LENGTH_METRIC_NAME]
    return list(text_length_metric.data.data_points)  # type: ignore[arg-type]


async def test_counted_text_length_is_recorded(
    client: CharacterCounterStub,
    get_recorded_metrics_by_name: Callable[[], dict[str, Metric]],
) -> None:
    """Each counted text adds its length to the histogram, so the dashboard can show the
    distribution of lengths and the number of requests."""
    await client.CountCharacters(CountCharactersRequest(text_to_count="hello"))
    await client.CountCharacters(CountCharactersRequest(text_to_count="hello world"))

    [text_length] = get_text_lengths(get_recorded_metrics_by_name())
    assert text_length.attributes == {}
    assert text_length.count == 2
    assert text_length.sum == 16
    assert text_length.min == 5
    assert text_length.max == 11


async def test_rejected_text_length_is_recorded_with_its_error_type(
    client: CharacterCounterStub,
    get_recorded_metrics_by_name: Callable[[], dict[str, Metric]],
) -> None:
    """A text over the limit is recorded with error.type, and the request still rejected."""
    text_over_the_limit = "a" * (MAX_CHARACTER_COUNT + 1)
    with pytest.raises(AioRpcError):
        await client.CountCharacters(CountCharactersRequest(text_to_count=text_over_the_limit))

    [text_length] = get_text_lengths(get_recorded_metrics_by_name())
    assert text_length.attributes == {"error.type": TEXT_TOO_LONG_ERROR_TYPE}
    assert text_length.count == 1
    assert text_length.sum == MAX_CHARACTER_COUNT + 1


async def test_text_length_buckets_split_at_the_character_limit(
    client: CharacterCounterStub,
    get_recorded_metrics_by_name: Callable[[], dict[str, Metric]],
) -> None:
    """The limit is a bucket boundary, so a text at the limit and one just over it land in
    different buckets."""
    await client.CountCharacters(CountCharactersRequest(text_to_count="a" * MAX_CHARACTER_COUNT))

    [text_length] = get_text_lengths(get_recorded_metrics_by_name())
    limit_bucket_index = list(text_length.explicit_bounds).index(MAX_CHARACTER_COUNT)
    assert text_length.bucket_counts[limit_bucket_index] == 1
