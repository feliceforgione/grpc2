import logging
from collections.abc import Callable

import pytest
from grpc import StatusCode
from grpc.aio import AioRpcError
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.trace import SpanKind

from character_count_grpc.character_counter_servicer import MAX_CHARACTER_COUNT
from character_count_proto.character_counter_pb2 import CountCharactersRequest
from character_count_proto.character_counter_pb2_grpc import CharacterCounterStub


@pytest.mark.parametrize(
    ("text_to_count", "expected_character_count"),
    [
        ("hello", 5),  # one per ASCII letter
        ("hello world", 11),  # spaces count as characters
        ("", 0),  # an empty text has no characters
        ("¿Szép?👋", 7),  # each Unicode code point counts once, not each UTF-8 byte
        ("a" * MAX_CHARACTER_COUNT, MAX_CHARACTER_COUNT),  # the limit itself is allowed
        ("👋" * MAX_CHARACTER_COUNT, MAX_CHARACTER_COUNT),  # limit is in code points, not bytes
    ],
)
async def test_count_characters_returns_the_number_of_characters(
    client: CharacterCounterStub, text_to_count: str, expected_character_count: int
) -> None:
    response = await client.CountCharacters(CountCharactersRequest(text_to_count=text_to_count))

    assert response.character_count == expected_character_count


async def test_count_characters_rejects_text_over_the_limit(client: CharacterCounterStub) -> None:
    text_over_the_limit = "a" * (MAX_CHARACTER_COUNT + 1)
    with pytest.raises(AioRpcError) as error_info:
        await client.CountCharacters(CountCharactersRequest(text_to_count=text_over_the_limit))

    assert error_info.value.code() == StatusCode.INVALID_ARGUMENT
    assert error_info.value.details() == (
        f"Text has {MAX_CHARACTER_COUNT + 1} characters; the maximum is {MAX_CHARACTER_COUNT}"
    )


async def test_count_characters_logs_the_count_but_not_the_text(
    client: CharacterCounterStub, caplog: pytest.LogCaptureFixture
) -> None:
    """The user's text stays out of the logs, which are sent to Loki."""
    valid_text = "hello"
    with caplog.at_level(logging.INFO):
        await client.CountCharacters(CountCharactersRequest(text_to_count=valid_text))

    [log_message] = [record.getMessage() for record in caplog.records]
    assert log_message == "Counted 5 characters"
    assert valid_text not in caplog.text


async def test_count_characters_records_a_server_span(
    client: CharacterCounterStub,
    get_finished_spans_by_kind: Callable[[], dict[SpanKind, ReadableSpan]],
) -> None:
    await client.CountCharacters(CountCharactersRequest(text_to_count="mock text"))

    server_span = get_finished_spans_by_kind()[SpanKind.SERVER]
    assert server_span.name == "/character_count.v1.CharacterCounter/CountCharacters"
