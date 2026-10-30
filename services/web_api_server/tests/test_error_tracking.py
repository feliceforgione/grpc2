import json
from collections.abc import Callable
from unittest.mock import Mock

from fastapi.testclient import TestClient
from grpc import StatusCode
from grpc.aio import AioRpcError
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.trace import format_span_id, format_trace_id
from sentry_sdk.types import Event

from utils.language_name import LanguageName
from web_api_server.main import app

TRANSLATE_URL = "/api/translate/"
TEXT_TO_TRANSLATE = "mock text to translate"
VALID_JSON_BODY = {"text": TEXT_TO_TRANSLATE, "language": LanguageName.ITALIAN}


def test_unexpected_error_sends_one_sentry_event_tagged_with_its_trace(
    mock_translate_grpc_client: Mock,
    get_sentry_events: Callable[[], list[Event]],
    get_finished_spans: Callable[[], tuple[ReadableSpan, ...]],
) -> None:
    """Sentry captures the exception after the request's span has ended, so the tags come from
    the server_request_hook that ran when the span started."""
    mock_translate_grpc_client.Translate.side_effect = ValueError("unexpected bug")

    response = TestClient(app, raise_server_exceptions=False).post(
        TRANSLATE_URL, json=VALID_JSON_BODY
    )

    assert response.status_code == 500
    [sentry_event] = get_sentry_events()
    [server_span] = get_finished_spans()
    assert server_span.context is not None
    [exception] = sentry_event["exception"]["values"]
    assert exception["type"] == "ValueError"
    assert sentry_event["tags"]["trace_id"] == format_trace_id(server_span.context.trace_id)
    assert sentry_event["tags"]["span_id"] == format_span_id(server_span.context.span_id)


def test_sentry_event_holds_no_request_body_or_headers(
    mock_translate_grpc_client: Mock,
    get_sentry_events: Callable[[], list[Event]],
) -> None:
    mock_translate_grpc_client.Translate.side_effect = ValueError("unexpected bug")

    TestClient(app, raise_server_exceptions=False).post(TRANSLATE_URL, json=VALID_JSON_BODY)

    [sentry_event] = get_sentry_events()
    assert not sentry_event["request"].get("data")
    assert not sentry_event["request"].get("headers")
    assert TEXT_TO_TRANSLATE not in json.dumps(sentry_event, default=str)


def test_failed_grpc_call_sends_no_sentry_event(
    mock_translate_grpc_client: Mock,
    get_sentry_events: Callable[[], list[Event]],
) -> None:
    """The web API answers a failed gRPC call with a 5xx and logs a warning, not an error: the
    translate service reports the failure itself, so Sentry gets one event for it, not two."""
    mock_translate_grpc_client.Translate.side_effect = AioRpcError(
        StatusCode.INTERNAL, Mock(), Mock(), details="upstream failure", debug_error_string=None
    )

    TestClient(app).post(TRANSLATE_URL, json=VALID_JSON_BODY)

    assert get_sentry_events() == []
