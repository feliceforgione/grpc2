"""Fixtures shared by the tests of every service and package."""

from collections.abc import Callable, Iterator

import pytest
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import set_tracer_provider


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
