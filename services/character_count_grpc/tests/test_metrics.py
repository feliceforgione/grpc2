from collections.abc import Callable

import pytest
from grpc.aio import AioRpcError
from opentelemetry.sdk.metrics.export import HistogramDataPoint, Metric

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
    word_1 = "hello"
    word_2 = "hello world"

    await client.CountCharacters(CountCharactersRequest(text_to_count="hello"))
    await client.CountCharacters(CountCharactersRequest(text_to_count="hello world"))

    [text_length] = get_text_lengths(get_recorded_metrics_by_name())
    assert text_length.attributes == {"is_over_limit": False}
    assert text_length.count == 2
    assert text_length.sum == len(word_1) + len(word_2)
    assert text_length.min == min(len(word_1), len(word_2))
    assert text_length.max == max(len(word_1), len(word_2))


async def test_rejected_text_length_is_recorded_as_over_limit(
    client: CharacterCounterStub,
    get_recorded_metrics_by_name: Callable[[], dict[str, Metric]],
) -> None:
    """A text over the limit is recorded with is_over_limit, and the request still rejected."""
    text_over_the_limit = "a" * (MAX_CHARACTER_COUNT + 1)
    with pytest.raises(AioRpcError):
        await client.CountCharacters(CountCharactersRequest(text_to_count=text_over_the_limit))

    [text_length] = get_text_lengths(get_recorded_metrics_by_name())
    assert text_length.attributes == {"is_over_limit": True}
    assert text_length.count == 1
    assert text_length.sum == MAX_CHARACTER_COUNT + 1
