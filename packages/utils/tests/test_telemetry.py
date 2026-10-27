import os
from unittest.mock import patch

from opentelemetry.sdk.resources import SERVICE_NAME

from utils.telemetry import create_tracer_provider

MOCK_SERVICE_NAME = "foo"


def test_create_tracer_provider_tags_spans_with_service_name() -> None:
    tracer_provider = create_tracer_provider(MOCK_SERVICE_NAME)

    assert tracer_provider.resource.attributes[SERVICE_NAME] == MOCK_SERVICE_NAME


def test_create_tracer_provider_reads_resource_attributes_from_env() -> None:
    deployment_environment = "test"

    with patch.dict(
        os.environ, {"OTEL_RESOURCE_ATTRIBUTES": f"deployment.environment={deployment_environment}"}
    ):
        tracer_provider = create_tracer_provider(MOCK_SERVICE_NAME)

    assert tracer_provider.resource.attributes["deployment.environment"] == deployment_environment


def test_create_tracer_provider_exports_spans_over_otlp() -> None:
    with patch("utils.telemetry.OTLPSpanExporter") as mock_otlp_span_exporter:
        tracer_provider = create_tracer_provider(MOCK_SERVICE_NAME)
        tracer_provider.get_tracer(__name__).start_span("foo").end()
        tracer_provider.force_flush()

    mock_otlp_span_exporter.return_value.export.assert_called_once()
