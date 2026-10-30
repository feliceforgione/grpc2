import json
from collections.abc import Callable
from unittest.mock import Mock

import grpc.aio
import pytest
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.trace import SpanKind, format_span_id, format_trace_id
from sentry_sdk.types import Event

from translate_proto.translator_pb2 import LANGUAGE_ITALIAN, TranslateRequest
from translate_proto.translator_pb2_grpc import TranslationStub

TEXT_TO_TRANSLATE = "mock text to translate"


async def test_failed_translation_sends_one_sentry_event_tagged_with_its_trace(
    mock_chat_gpt_translator_translate: Mock,
    translate_grpc_channel: grpc.aio.Channel,
    get_sentry_events: Callable[[], list[Event]],
    get_finished_spans_by_kind: Callable[[], dict[SpanKind, ReadableSpan]],
) -> None:
    """The servicer logs the failure inside the RPC's span, and gRPC's own later log of the same
    exception is dropped as a duplicate, so Sentry gets one event it can link to the trace."""
    mock_chat_gpt_translator_translate.side_effect = RuntimeError("upstream failure")
    request = TranslateRequest(text=TEXT_TO_TRANSLATE, language=LANGUAGE_ITALIAN)

    with pytest.raises(grpc.aio.AioRpcError):
        await TranslationStub(translate_grpc_channel).Translate(request)  # type: ignore[no-untyped-call]

    [sentry_event] = get_sentry_events()
    server_span_context = get_finished_spans_by_kind()[SpanKind.SERVER].context
    assert server_span_context is not None
    assert sentry_event["logentry"]["formatted"] == "Translation of 22 characters to italian failed"
    [exception] = sentry_event["exception"]["values"]
    assert exception["type"] == "RuntimeError"
    assert sentry_event["tags"]["trace_id"] == format_trace_id(server_span_context.trace_id)
    assert sentry_event["tags"]["span_id"] == format_span_id(server_span_context.span_id)


async def test_sentry_event_holds_no_user_text(
    mock_chat_gpt_translator_translate: Mock,
    translate_grpc_channel: grpc.aio.Channel,
    get_sentry_events: Callable[[], list[Event]],
) -> None:
    """Local variables are left out of the stack trace, since the servicer's hold the text."""
    mock_chat_gpt_translator_translate.side_effect = RuntimeError("upstream failure")
    request = TranslateRequest(text=TEXT_TO_TRANSLATE, language=LANGUAGE_ITALIAN)

    with pytest.raises(grpc.aio.AioRpcError):
        await TranslationStub(translate_grpc_channel).Translate(request)  # type: ignore[no-untyped-call]

    [sentry_event] = get_sentry_events()
    [exception] = sentry_event["exception"]["values"]
    assert all("vars" not in frame for frame in exception["stacktrace"]["frames"])
    assert TEXT_TO_TRANSLATE not in json.dumps(sentry_event, default=str)
