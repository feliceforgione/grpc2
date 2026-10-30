from collections.abc import Callable
from unittest.mock import Mock

from fastapi.testclient import TestClient
from grpc import StatusCode
from grpc.aio import AioRpcError
from opentelemetry.sdk._logs import ReadableLogRecord
from opentelemetry.sdk.trace import ReadableSpan

from utils.language_name import LanguageName
from web_api_server.main import app

TRANSLATE_URL = "/api/translate/"
VALID_JSON_BODY = {"text": "mock text to translate", "language": LanguageName.ITALIAN}


def test_failed_grpc_call_warning_joins_the_request_span(
    mock_translate_grpc_client: Mock,
    get_finished_log_records: Callable[[], tuple[ReadableLogRecord, ...]],
    get_finished_spans: Callable[[], tuple[ReadableSpan, ...]],
) -> None:
    """The warning about a failed gRPC call carries the request's trace and span IDs."""
    mock_translate_grpc_client.Translate.side_effect = AioRpcError(
        StatusCode.INTERNAL, Mock(), Mock(), details="upstream failure", debug_error_string=None
    )

    TestClient(app).post(TRANSLATE_URL, json=VALID_JSON_BODY)

    [readable_log_record] = get_finished_log_records()
    log_record = readable_log_record.log_record
    [server_span] = get_finished_spans()
    assert server_span.context is not None
    assert log_record.severity_text == "WARN"
    assert str(log_record.body).startswith("gRPC call failed for /api/translate/")
    assert log_record.trace_id == server_span.context.trace_id
    assert log_record.span_id == server_span.context.span_id
