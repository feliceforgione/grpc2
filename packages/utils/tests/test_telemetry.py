import os
from unittest.mock import patch

from opentelemetry.sdk.resources import SERVICE_NAME

from utils.telemetry import create_tracer_provider

VALID_SERVICE_NAME = "translate-grpc"


def test_create_tracer_provider_tags_spans_with_service_name() -> None:
    tracer_provider = create_tracer_provider(VALID_SERVICE_NAME)

    assert tracer_provider.resource.attributes[SERVICE_NAME] == VALID_SERVICE_NAME


def test_create_tracer_provider_reads_resource_attributes_from_env() -> None:
    with patch.dict(os.environ, {"OTEL_RESOURCE_ATTRIBUTES": "deployment.environment=test"}):
        tracer_provider = create_tracer_provider(VALID_SERVICE_NAME)

    assert tracer_provider.resource.attributes["deployment.environment"] == "test"
