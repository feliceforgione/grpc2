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
