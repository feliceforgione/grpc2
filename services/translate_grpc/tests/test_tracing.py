from collections.abc import Callable
from unittest.mock import Mock

import grpc.aio
import pytest
from grpc_health.v1.health_pb2 import HealthCheckRequest
from grpc_health.v1.health_pb2_grpc import HealthStub
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.trace import SpanKind, StatusCode

from translate_grpc.translation import OPENAI_MODEL, translate_text
from translate_proto.translator_pb2 import LANGUAGE_ITALIAN, TranslateRequest
from translate_proto.translator_pb2_grpc import TranslationStub
from utils.language_name import LanguageName

VALID_TEXT = "hello"
VALID_LANGUAGE = LanguageName.ITALIAN
VALID_TRANSLATE_REQUEST = TranslateRequest(text=VALID_TEXT, language=LANGUAGE_ITALIAN)


async def test_translate_records_a_server_span(
    mock_chat_gpt_translator_translate: Mock,
    translate_grpc_channel: grpc.aio.Channel,
    get_finished_spans_by_kind: Callable[[], dict[SpanKind, ReadableSpan]],
) -> None:
    mock_chat_gpt_translator_translate.return_value = "mock"

    await TranslationStub(translate_grpc_channel).Translate(VALID_TRANSLATE_REQUEST)  # type: ignore[no-untyped-call]

    server_span = get_finished_spans_by_kind()[SpanKind.SERVER]
    assert server_span.name == "/translator.v1.Translation/Translate"


async def test_translate_span_joins_the_callers_trace(
    mock_chat_gpt_translator_translate: Mock,
    translate_grpc_channel: grpc.aio.Channel,
    get_finished_spans_by_kind: Callable[[], dict[SpanKind, ReadableSpan]],
) -> None:
    """The server continues the trace named in the call's `traceparent` metadata.

    This is how the web API server's trace follows its call into this server.
    """
    mock_chat_gpt_translator_translate.return_value = "mock"
    trace_id = 0x0AF7651916CD43DD8448EB211C80319C
    parent_span_id = 0xB7AD6B7169203331
    traceparent = f"00-{trace_id:032x}-{parent_span_id:016x}-01"

    await TranslationStub(translate_grpc_channel).Translate(  # type: ignore[no-untyped-call]
        VALID_TRANSLATE_REQUEST, metadata=[("traceparent", traceparent)]
    )

    span = get_finished_spans_by_kind()[SpanKind.SERVER]
    assert span.context is not None
    assert span.context.trace_id == trace_id
    assert span.parent is not None
    assert span.parent.span_id == parent_span_id


async def test_health_check_records_no_span(
    translate_grpc_channel: grpc.aio.Channel,
    get_finished_spans: Callable[[], tuple[ReadableSpan, ...]],
) -> None:
    """Docker's health checks are left out, so they don't bury the translation spans."""
    await HealthStub(translate_grpc_channel).Check(HealthCheckRequest())

    assert get_finished_spans() == ()


async def test_openai_call_records_client_span_under_the_server_span(
    mock_chat_gpt_translator_translate: Mock,
    translate_grpc_channel: grpc.aio.Channel,
    get_finished_spans_by_kind: Callable[[], dict[SpanKind, ReadableSpan]],
) -> None:
    """The call to OpenAI joins the RPC's trace, so it shows how much of the RPC it took."""
    mock_chat_gpt_translator_translate.return_value = "mock"

    await TranslationStub(translate_grpc_channel).Translate(VALID_TRANSLATE_REQUEST)  # type: ignore[no-untyped-call]

    spans_by_kind = get_finished_spans_by_kind()
    server_span = spans_by_kind[SpanKind.SERVER]
    client_span = spans_by_kind[SpanKind.CLIENT]
    assert client_span.parent is not None
    assert server_span.context is not None
    assert client_span.parent.span_id == server_span.context.span_id


def test_openai_span_records_model_language_and_text_lengths(
    mock_chat_gpt_translator_translate: Mock,
    get_finished_spans: Callable[[], tuple[ReadableSpan, ...]],
) -> None:
    """The span uses the GenAI semantic conventions' names, and never records the text itself."""
    mock_chat_gpt_translator_translate.return_value = ' "mock"\n'

    translate_text(VALID_TEXT, VALID_LANGUAGE)

    [span] = get_finished_spans()
    assert span.name == f"chat {OPENAI_MODEL}"
    assert span.kind == SpanKind.CLIENT
    assert span.attributes == {
        "gen_ai.operation.name": "chat",
        "gen_ai.provider.name": "openai",
        "gen_ai.request.model": OPENAI_MODEL,
        "translation.target_language": VALID_LANGUAGE,
        "translation.text_length": len(VALID_TEXT),
        # Measured before strip_added_quotes, so it is the length OpenAI sent back.
        "translation.answer_length": len(' "mock"\n'),
    }


def test_openai_span_records_failed_call_as_error(
    mock_chat_gpt_translator_translate: Mock,
    get_finished_spans: Callable[[], tuple[ReadableSpan, ...]],
) -> None:
    mock_chat_gpt_translator_translate.side_effect = RuntimeError("upstream failure")

    with pytest.raises(RuntimeError):
        translate_text(VALID_TEXT, VALID_LANGUAGE)

    [span] = get_finished_spans()
    assert span.status.status_code == StatusCode.ERROR
    assert [event.name for event in span.events] == ["exception"]
