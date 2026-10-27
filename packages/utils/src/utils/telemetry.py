"""Set up the OpenTelemetry SDK that turns the services' OpenTelemetry API calls into data.

Code that records telemetry imports only the API (opentelemetry.trace). Until a service calls
setup_telemetry(), those calls are no-ops, which is why tests that never call it stay quiet.
"""

from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.trace import set_tracer_provider


def create_tracer_provider(service_name: str) -> TracerProvider:
    """Create a tracer provider that tags spans with service_name, prints them to stdout and
    sends them over OTLP gRPC."""
    # Resource.create also reads the standard OTEL_RESOURCE_ATTRIBUTES env var.
    resource = Resource.create({SERVICE_NAME: service_name})
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
    # OTLPSpanExporter reads the standard OTEL_EXPORTER_OTLP_ENDPOINT env var.
    tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    return tracer_provider


def setup_telemetry(service_name: str) -> None:
    """Install the tracer provider globally; call it once, from the service's main()."""
    # The provider flushes its pending spans when the process exits.
    set_tracer_provider(create_tracer_provider(service_name))
