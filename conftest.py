"""Fixtures shared by the tests of every service and package."""

from collections.abc import Callable, Iterator

import pytest
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import SpanKind, set_tracer_provider


@pytest.fixture(scope="session")
def set_up_in_memory_tracer_provider() -> InMemorySpanExporter:
    """Install a global tracer provider that keeps spans in memory, and return its exporter.

    OpenTelemetry lets a process set the global tracer provider only once, so the tests of
    every service share this one; it lives here rather than in a service's conftest.py.
    """
    span_exporter = InMemorySpanExporter()
    tracer_provider = TracerProvider()
    tracer_provider.add_span_processor(SimpleSpanProcessor(span_exporter))
    set_tracer_provider(tracer_provider)
    return span_exporter


@pytest.fixture
def get_finished_spans(
    set_up_in_memory_tracer_provider: InMemorySpanExporter,
) -> Iterator[Callable[[], tuple[ReadableSpan, ...]]]:
    """Clear the spans earlier tests recorded, and yield a function returning this test's spans."""
    span_exporter = set_up_in_memory_tracer_provider
    span_exporter.clear()
    yield span_exporter.get_finished_spans


@pytest.fixture
def get_finished_spans_by_kind(
    get_finished_spans: Callable[[], tuple[ReadableSpan, ...]],
) -> Callable[[], dict[SpanKind, ReadableSpan]]:
    """Return a function mapping each SpanKind to this test's one span of that kind.

    For calls that record a span of each kind, e.g. a SERVER span and the CLIENT span under it.
    """

    def get_spans_by_kind() -> dict[SpanKind, ReadableSpan]:
        spans = get_finished_spans()
        spans_by_kind = {span.kind: span for span in spans}
        # A second span of the same kind would replace the first one in the dict.
        assert len(spans_by_kind) == len(spans), f"more than one span of a kind: {spans}"
        return spans_by_kind

    return get_spans_by_kind
