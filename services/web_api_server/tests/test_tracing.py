from collections.abc import Iterator
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi.testclient import TestClient
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import SpanKind, set_tracer_provider

from translate_proto.translator_pb2 import TranslateResponse
from utils.language_name import LanguageName
from web_api_server.main import app
from web_api_server.routers.translate import get_translate_grpc_client

TRANSLATE_URL = "/api/translate/"
VALID_JSON_BODY = {"text": "hello", "language": LanguageName.ITALIAN}

# OpenTelemetry lets a process set the global tracer provider only once, so every test in this
# module shares one exporter and clears it before each test.
SPAN_EXPORTER = InMemorySpanExporter()


@pytest.fixture(scope="module", autouse=True)
def set_up_in_memory_tracer_provider() -> None:
    """Send the app's spans to SPAN_EXPORTER instead of the console."""
    tracer_provider = TracerProvider()
    tracer_provider.add_span_processor(SimpleSpanProcessor(SPAN_EXPORTER))
    set_tracer_provider(tracer_provider)


@pytest.fixture(autouse=True)
def clear_spans_in_span_exporter() -> Iterator[None]:
    SPAN_EXPORTER.clear()
    yield


@pytest.fixture
def mock_translate_grpc_client() -> Iterator[Mock]:
    """Replace the gRPC client the route depends on with a mock whose `Translate` is async."""
    translate_grpc_client_mock = Mock(Translate=AsyncMock())
    app.dependency_overrides[get_translate_grpc_client] = lambda: translate_grpc_client_mock
    yield translate_grpc_client_mock
    app.dependency_overrides.clear()


def test_request_records_one_server_span(mock_translate_grpc_client: Mock) -> None:
    """Each request records a single SERVER span covering the whole request.

    By default the FastAPI instrumentation also records a child span for every ASGI
    `receive` call and `send` call. main.py excludes those, so this span is
    the only one.
    """
    mock_translate_grpc_client.Translate.return_value = TranslateResponse(translated_text="ciao")

    TestClient(app).post(TRANSLATE_URL, json=VALID_JSON_BODY)

    [span] = SPAN_EXPORTER.get_finished_spans()
    assert span.name == f"POST {TRANSLATE_URL}"
    assert span.kind == SpanKind.SERVER
    assert span.attributes is not None
    assert span.attributes["http.route"] == TRANSLATE_URL
    assert span.attributes["http.status_code"] == 200


@pytest.mark.usefixtures("mock_translate_grpc_client")
def test_request_span_records_error_status_code() -> None:
    """A request the route rejects still records a span, with the error status code."""
    invalid_json_body = {
        "text": "",
        "language": None,
    }
    TestClient(app).post(TRANSLATE_URL, json=invalid_json_body)

    [span] = SPAN_EXPORTER.get_finished_spans()
    assert span.attributes is not None
    assert span.attributes["http.status_code"] == 422
