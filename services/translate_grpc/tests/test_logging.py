import logging
from collections.abc import Callable
from unittest.mock import Mock

import grpc.aio
import pytest
from opentelemetry.sdk._logs import ReadableLogRecord
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.trace import SpanKind

from translate_proto.translator_pb2 import LANGUAGE_ITALIAN, TranslateRequest
from translate_proto.translator_pb2_grpc import TranslationStub


async def test_translate_log_record_joins_the_rpc_span(
    mock_chat_gpt_translator_translate: Mock,
    translate_grpc_channel: grpc.aio.Channel,
    caplog: pytest.LogCaptureFixture,
    get_finished_log_records: Callable[[], tuple[ReadableLogRecord, ...]],
    get_finished_spans_by_kind: Callable[[], dict[SpanKind, ReadableSpan]],
) -> None:
    """The servicer's log line carries the RPC's trace and span IDs, so Grafana can link them."""
    mock_chat_gpt_translator_translate.return_value = "mock translation"
    request = TranslateRequest(text="mock text to translate", language=LANGUAGE_ITALIAN)

    with caplog.at_level(logging.INFO):
        await TranslationStub(translate_grpc_channel).Translate(request)  # type: ignore[no-untyped-call]

    [log_record] = [
        readable_log_record.log_record
        for readable_log_record in get_finished_log_records()
        if str(readable_log_record.log_record.body).startswith("Translated ")
    ]
    server_span = get_finished_spans_by_kind()[SpanKind.SERVER]
    assert server_span.context is not None
    assert log_record.severity_text == "INFO"
    assert log_record.trace_id == server_span.context.trace_id
    assert log_record.span_id == server_span.context.span_id
