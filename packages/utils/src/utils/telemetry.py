"""Set up the OpenTelemetry SDK that turns the services' OpenTelemetry API calls into data.

Code that records telemetry imports only the API (opentelemetry.trace, opentelemetry.metrics).
Until a service calls setup_telemetry(), those calls are no-ops, which is why tests that never
call it stay quiet.
"""

from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.metrics import set_meter_provider
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


def setup_telemetry(service_name: str) -> None:
    """Install the tracer and meter providers globally; call it once, from the service's
    main()."""
    # The providers flush their pending spans and metrics when the process exits.
    set_tracer_provider(create_tracer_provider(service_name))
    set_meter_provider(create_meter_provider(service_name))
