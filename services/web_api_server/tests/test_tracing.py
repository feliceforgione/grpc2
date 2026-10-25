from collections.abc import AsyncIterator, Callable
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.trace import SpanKind

from translate_proto.translator_pb2 import TranslateResponse
from translate_proto.translator_pb2_grpc import TranslationStub
from utils.language_name import LanguageName
from web_api_server.grpc_channel import open_translate_grpc_channel
from web_api_server.main import app

TRANSLATE_URL = "/api/translate/"
VALID_JSON_BODY = {"text": "hello", "language": LanguageName.ITALIAN}


def test_request_records_one_server_span(
    mock_translate_grpc_client: Mock, get_finished_spans: Callable[[], tuple[ReadableSpan, ...]]
) -> None:
    """Each request records a single SERVER span covering the whole request.

    By default the FastAPI instrumentation also records a child span for every ASGI
    `receive` call and `send` call. main.py excludes those, so this span is
    the only one.
    """
    mock_translate_grpc_client.Translate.return_value = TranslateResponse(translated_text="ciao")

    TestClient(app).post(TRANSLATE_URL, json=VALID_JSON_BODY)

    [span] = get_finished_spans()
    assert span.name == f"POST {TRANSLATE_URL}"
    assert span.kind == SpanKind.SERVER
    assert span.attributes is not None
    assert span.attributes["http.route"] == TRANSLATE_URL
    assert span.attributes["http.status_code"] == 200


@pytest.mark.usefixtures("mock_translate_grpc_client")
def test_request_span_records_error_status_code(
    get_finished_spans: Callable[[], tuple[ReadableSpan, ...]],
) -> None:
    """A request the route rejects still records a span, with the error status code."""
    invalid_json_body = {
        "text": "",
        "language": None,
    }
    TestClient(app).post(TRANSLATE_URL, json=invalid_json_body)

    [span] = get_finished_spans()
    assert span.attributes is not None
    assert span.attributes["http.status_code"] == 422


def test_health_route_records_no_span(
    get_finished_spans: Callable[[], tuple[ReadableSpan, ...]],
) -> None:
    """Docker's health checks are left out, so they don't bury the translation spans."""
    TestClient(app).get("/health")

    assert get_finished_spans() == ()


@pytest.fixture
async def mock_translation_servicer_behind_app(
    mock_translation_servicer: Mock,
    set_translate_grpc_client: Callable[[TranslationStub | Mock], None],
) -> AsyncIterator[Mock]:
    """Point the app at `mock_translation_servicer` through the same channel main.py opens.

    Going through that channel is what makes the test cover its tracing interceptors.
    """
    mock_translation_servicer.Translate.return_value = TranslateResponse(translated_text="ciao")
    async with open_translate_grpc_channel(mock_translation_servicer.address) as grpc_channel:
        set_translate_grpc_client(TranslationStub(grpc_channel))  # type: ignore[no-untyped-call]
        yield mock_translation_servicer


async def test_grpc_call_records_client_span_in_the_request_trace(
    mock_translation_servicer_behind_app: Mock,
    get_finished_spans: Callable[[], tuple[ReadableSpan, ...]],
) -> None:
    """The call to the translate service records a CLIENT span under the request's SERVER span.

    It also sends the trace context in the call's metadata, so the translate server can join
    the trace. AsyncClient runs the app on this test's event loop, which the gRPC channel
    needs; TestClient would run it on another one.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://mock") as client:
        await client.post(TRANSLATE_URL, json=VALID_JSON_BODY)

    spans_by_kind = {span.kind: span for span in get_finished_spans()}
    server_span = spans_by_kind[SpanKind.SERVER]
    client_span = spans_by_kind[SpanKind.CLIENT]
    assert client_span.name == "/translator.v1.Translation/Translate"
    assert client_span.parent is not None
    assert server_span.context is not None
    assert client_span.parent.span_id == server_span.context.span_id
    # traceparent is "<version>-<trace id>-<parent span id>-<flags>".
    assert client_span.context is not None
    _, servicer_context = mock_translation_servicer_behind_app.Translate.await_args.args
    received_traceparent = dict(servicer_context.invocation_metadata())["traceparent"]
    _, trace_id, parent_span_id, _ = received_traceparent.split("-")
    assert int(trace_id, 16) == client_span.context.trace_id
    assert int(parent_span_id, 16) == client_span.context.span_id
