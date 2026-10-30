"""Set up the OpenTelemetry SDK that turns the services' OpenTelemetry API calls into data.

Code that records telemetry imports only the API (opentelemetry.trace, opentelemetry.metrics),
or Python's logging. Until a service calls setup_telemetry(), those calls are no-ops, apart from
logging's own handlers, which is why tests that never call it stay quiet.

The logs SDK is still experimental, which is why its modules (opentelemetry._logs,
opentelemetry.sdk._logs and the OTLP _log_exporter) have a leading underscore; their names may
change in a later release.
"""

from logging import getLogger

from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.instrumentation.logging.handler import LoggingHandler
from opentelemetry.metrics import set_meter_provider
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.trace import set_tracer_provider


def create_service_resource(service_name: str) -> Resource:
    """Create the resource that tags all of a service's telemetry with service_name."""
    # Resource.create also reads the standard OTEL_RESOURCE_ATTRIBUTES env var.
    return Resource.create({SERVICE_NAME: service_name})


def create_tracer_provider(service_name: str) -> TracerProvider:
    """Create a tracer provider that tags spans with service_name, prints them to stdout and
    sends them over OTLP gRPC."""
    tracer_provider = TracerProvider(resource=create_service_resource(service_name))
    tracer_provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
    # OTLPSpanExporter reads the standard OTEL_EXPORTER_OTLP_ENDPOINT env var.
    tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    return tracer_provider


def create_meter_provider(service_name: str) -> MeterProvider:
    """Create a meter provider that tags metrics with service_name and periodically sends them
    over OTLP HTTP."""
    # Prometheus's OTLP receiver accepts only HTTP, unlike Tempo, so this exporter reads the
    # metrics-only OTEL_EXPORTER_OTLP_METRICS_ENDPOINT env var, which keeps metrics away from
    # the gRPC endpoint in OTEL_EXPORTER_OTLP_ENDPOINT that the spans go to.
    # PeriodicExportingMetricReader exports every OTEL_METRIC_EXPORT_INTERVAL ms (60s default).
    metric_reader = PeriodicExportingMetricReader(OTLPMetricExporter())
    return MeterProvider(
        resource=create_service_resource(service_name), metric_readers=[metric_reader]
    )


def create_logger_provider(service_name: str) -> LoggerProvider:
    """Create a logger provider that tags log records with service_name and sends them over
    OTLP HTTP."""
    # Like the metric exporter, OTLPLogExporter reads its own OTEL_EXPORTER_OTLP_LOGS_ENDPOINT
    # env var, since Loki's OTLP endpoint accepts only HTTP.
    logger_provider = LoggerProvider(resource=create_service_resource(service_name))
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(OTLPLogExporter()))
    return logger_provider


def add_logging_handler() -> None:
    """Send every record Python's logging lets through to the global logger provider.

    The handler goes on the root logger, alongside any handler logging.basicConfig() added, so
    the logs still print to stdout too. Each record carries the trace and span IDs of the span
    that was current when it was logged.
    """
    getLogger().addHandler(LoggingHandler())


def setup_telemetry(service_name: str) -> None:
    """Install the tracer, meter and logger providers globally, and send Python's logging
    to the logger provider; call it once, from the service's main()."""
    # The providers flush their pending spans, metrics and logs when the process exits.
    set_tracer_provider(create_tracer_provider(service_name))
    set_meter_provider(create_meter_provider(service_name))
    set_logger_provider(create_logger_provider(service_name))
    add_logging_handler()
