import os
from unittest.mock import patch

from opentelemetry.sdk.resources import SERVICE_NAME

from utils.telemetry import create_logger_provider, create_meter_provider, create_tracer_provider

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


def test_create_meter_provider_exports_metrics_over_otlp_tagged_with_service_name() -> None:
    with patch("utils.telemetry.OTLPMetricExporter") as mock_otlp_metric_exporter:
        meter_provider = create_meter_provider(MOCK_SERVICE_NAME)
        meter_provider.get_meter(__name__).create_counter("foo").add(1)
        meter_provider.force_flush()

    mock_otlp_metric_exporter.return_value.export.assert_called_once()
    metrics_data = mock_otlp_metric_exporter.return_value.export.call_args.args[0]
    resource = metrics_data.resource_metrics[0].resource
    assert resource.attributes[SERVICE_NAME] == MOCK_SERVICE_NAME


def test_create_logger_provider_exports_logs_over_otlp_tagged_with_service_name() -> None:
    with patch("utils.telemetry.OTLPLogExporter") as mock_otlp_log_exporter:
        logger_provider = create_logger_provider(MOCK_SERVICE_NAME)
        logger_provider.get_logger(__name__).emit(body="foo")
        logger_provider.force_flush()

    mock_otlp_log_exporter.return_value.export.assert_called_once()
    [log_record] = mock_otlp_log_exporter.return_value.export.call_args.args[0]
    assert log_record.log_record.body == "foo"
    assert log_record.resource.attributes[SERVICE_NAME] == MOCK_SERVICE_NAME
