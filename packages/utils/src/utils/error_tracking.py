"""Send the services' errors to Sentry, which groups them and alerts on new ones.

Sentry only gets errors: uncaught exceptions and records logged at ERROR and above. Logs, traces
and metrics stay with Loki, Tempo and Prometheus, so Sentry's own tracing is left off.
"""

import os
from typing import Any

import sentry_sdk
from opentelemetry.trace import Span, SpanContext, format_span_id, format_trace_id, get_current_span
from sentry_sdk.types import Event, Hint


def create_trace_tags(span_context: SpanContext) -> dict[str, str]:
    """Create the Sentry tags that find an error's trace in Tempo and its log lines in Loki."""
    return {
        "trace_id": format_trace_id(span_context.trace_id),
        "span_id": format_span_id(span_context.span_id),
    }


def add_trace_tags(event: Event, hint: Hint) -> Event:
    """Tag an error with the trace and span IDs of the span it was captured in, unless the
    request already tagged it."""
    span_context = get_current_span().get_span_context()
    if span_context.is_valid:
        tags = event.setdefault("tags", {})
        for name, value in create_trace_tags(span_context).items():
            tags.setdefault(name, value)
    return event


def tag_request_errors_with_trace(span: Span, scope: dict[str, Any]) -> None:
    """Tag the errors Sentry captures during an HTTP request with the request's trace.

    For FastAPIInstrumentor's server_request_hook, which runs when the request's span starts.
    Sentry captures an uncaught exception only after that span has ended, so add_trace_tags
    can't see it; Sentry's scope for the request keeps these tags until then.
    """
    span_context = span.get_span_context()
    if span_context.is_valid:
        sentry_sdk.get_isolation_scope().set_tags(create_trace_tags(span_context))


def create_sentry_options(sentry_dsn: str) -> dict[str, Any]:
    """Create the options to start Sentry with, sending errors to the project at sentry_dsn."""
    # The SDK reads SENTRY_ENVIRONMENT and SENTRY_RELEASE itself.
    return {
        "dsn": sentry_dsn,
        # No traces or profiles: Tempo has the traces. Nor Sentry's trace headers on outgoing
        # requests, which it adds even with tracing off, e.g. to the calls to OpenAI.
        "traces_sample_rate": None,
        "trace_propagation_targets": [],
        # Keep the user's text out of Sentry, as it's kept out of the spans and logs: no
        # request bodies, no local variables in stack frames (the servicer's hold the text),
        # and no IP addresses, cookies, headers or query strings that could identify the user.
        # data_collection replaces send_default_pii. Any category it leaves out is collected,
        # so every one is listed.
        "data_collection": {
            "user_info": False,
            "cookies": {"mode": "off"},
            "http_headers": {"request": {"mode": "off"}},
            "http_bodies": [],
            "url_query_params": {"mode": "off"},
            "graphql": {"document": False, "variables": False},
            "gen_ai": {"inputs": False, "outputs": False},
            "database_query_data": False,
            "queues": False,
            "stack_frame_variables": False,
        },
        "max_request_body_size": "never",
        "before_send": add_trace_tags,
    }


def setup_error_tracking(service_name: str) -> None:
    """Start sending errors to the Sentry project in SENTRY_DSN; call it once, from the
    service's main(). Without SENTRY_DSN, as in the tests and local runs, it sends nothing."""
    sentry_dsn = os.environ.get("SENTRY_DSN")
    if not sentry_dsn:
        return
    sentry_sdk.init(**create_sentry_options(sentry_dsn))
    sentry_sdk.set_tag("service", service_name)
