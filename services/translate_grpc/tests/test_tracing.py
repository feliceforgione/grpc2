from collections.abc import Callable
from unittest.mock import Mock

import grpc.aio
from grpc_health.v1.health_pb2 import HealthCheckRequest
from grpc_health.v1.health_pb2_grpc import HealthStub
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.trace import SpanKind

from translate_proto.translator_pb2 import LANGUAGE_ITALIAN, TranslateRequest
from translate_proto.translator_pb2_grpc import TranslationStub

VALID_TRANSLATE_REQUEST = TranslateRequest(text="hello", language=LANGUAGE_ITALIAN)


async def test_translate_records_one_server_span(
    mock_chat_gpt_translator_translate: Mock,
    channel: grpc.aio.Channel,
    get_finished_spans: Callable[[], tuple[ReadableSpan, ...]],
) -> None:
    mock_chat_gpt_translator_translate.return_value = "ciao"

    await TranslationStub(channel).Translate(VALID_TRANSLATE_REQUEST)  # type: ignore[no-untyped-call]

    [span] = get_finished_spans()
    assert span.name == "/translator.v1.Translation/Translate"
    assert span.kind == SpanKind.SERVER


async def test_translate_span_joins_the_callers_trace(
    mock_chat_gpt_translator_translate: Mock,
    channel: grpc.aio.Channel,
    get_finished_spans: Callable[[], tuple[ReadableSpan, ...]],
) -> None:
    """The server continues the trace named in the call's `traceparent` metadata.

    This is how the web API server's trace follows its call into this server.
    """
    mock_chat_gpt_translator_translate.return_value = "ciao"
    trace_id = 0x0AF7651916CD43DD8448EB211C80319C
    parent_span_id = 0xB7AD6B7169203331
    traceparent = f"00-{trace_id:032x}-{parent_span_id:016x}-01"

    await TranslationStub(channel).Translate(  # type: ignore[no-untyped-call]
        VALID_TRANSLATE_REQUEST, metadata=[("traceparent", traceparent)]
    )

    [span] = get_finished_spans()
    assert span.context is not None
    assert span.context.trace_id == trace_id
    assert span.parent is not None
    assert span.parent.span_id == parent_span_id


async def test_health_check_records_no_span(
    channel: grpc.aio.Channel,
    get_finished_spans: Callable[[], tuple[ReadableSpan, ...]],
) -> None:
    """Docker's health checks are left out, so they don't bury the translation spans."""
    await HealthStub(channel).Check(HealthCheckRequest())

    assert get_finished_spans() == ()
