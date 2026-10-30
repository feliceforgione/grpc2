from collections.abc import Callable
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from grpc import StatusCode
from grpc.aio import AioRpcError
from opentelemetry.sdk.metrics.export import HistogramDataPoint, Metric

from translate_proto.translator_pb2 import TranslateResponse
from utils.language_name import LanguageName
from web_api_server.main import app

REQUEST_DURATION_METRIC_NAME = "http.server.request.duration"
TRANSLATE_URL = "/api/translate/"
VALID_JSON_BODY = {"text": "hello", "language": LanguageName.ITALIAN}


def get_request_durations(metrics_by_name: dict[str, Metric]) -> list[HistogramDataPoint]:
    """Return the request duration histogram's data points, one per set of attributes."""
    request_duration_metric = metrics_by_name[REQUEST_DURATION_METRIC_NAME]
    return list(request_duration_metric.data.data_points)  # type: ignore[arg-type]


def test_request_records_its_duration_in_seconds(
    mock_translate_grpc_client: Mock,
    get_recorded_metrics_by_name: Callable[[], dict[str, Metric]],
) -> None:
    """Each request adds one sample to the duration histogram, labelled with its route.

    main.py opts into the stable HTTP conventions, which name the metric
    http.server.request.duration and record it in seconds.
    """
    mock_translate_grpc_client.Translate.return_value = TranslateResponse(translated_text="ciao")

    TestClient(app).post(TRANSLATE_URL, json=VALID_JSON_BODY)

    metrics_by_name = get_recorded_metrics_by_name()
    assert metrics_by_name[REQUEST_DURATION_METRIC_NAME].unit == "s"
    [request_duration] = get_request_durations(metrics_by_name)
    assert request_duration.count == 1
    assert request_duration.attributes == {
        "url.scheme": "http",
        "network.protocol.version": "1.1",
        "http.request.method": "POST",
        "http.route": TRANSLATE_URL,
        "http.response.status_code": 200,
    }


@pytest.mark.usefixtures("mock_translate_grpc_client")
def test_request_duration_records_error_status_code(
    get_recorded_metrics_by_name: Callable[[], dict[str, Metric]],
) -> None:
    """A request the route rejects is still timed, labelled with the error status code."""
    invalid_json_body = {"text": "", "language": None}

    TestClient(app).post(TRANSLATE_URL, json=invalid_json_body)

    [request_duration] = get_request_durations(get_recorded_metrics_by_name())
    assert request_duration.attributes is not None
    assert request_duration.attributes["http.response.status_code"] == 422


def test_failed_grpc_call_records_server_error_status_code(
    mock_translate_grpc_client: Mock,
    get_recorded_metrics_by_name: Callable[[], dict[str, Metric]],
) -> None:
    """A request the translate service fails is timed with its 5xx status code.

    The dashboard's availability panels count these 5xx responses as unavailable.
    """
    mock_translate_grpc_client.Translate.side_effect = AioRpcError(
        StatusCode.INTERNAL, Mock(), Mock(), details="upstream failure", debug_error_string=None
    )

    TestClient(app).post(TRANSLATE_URL, json=VALID_JSON_BODY)

    [request_duration] = get_request_durations(get_recorded_metrics_by_name())
    assert request_duration.attributes is not None
    assert request_duration.attributes["http.response.status_code"] == 502


def test_unknown_url_records_no_route(
    get_recorded_metrics_by_name: Callable[[], dict[str, Metric]],
) -> None:
    """A URL no route matches is timed without its path, so it adds no new series.

    Otherwise every URL a scanner tries would become its own Prometheus series.
    """
    TestClient(app).get("/wp-login.php")

    [request_duration] = get_request_durations(get_recorded_metrics_by_name())
    assert request_duration.attributes is not None
    assert request_duration.attributes["http.response.status_code"] == 404
    assert "http.route" not in request_duration.attributes
    assert "/wp-login.php" not in request_duration.attributes.values()


def test_health_route_records_no_duration(
    get_recorded_metrics_by_name: Callable[[], dict[str, Metric]],
) -> None:
    """Docker's health checks are left out, so they don't skew the request durations."""
    TestClient(app).get("/health")

    assert REQUEST_DURATION_METRIC_NAME not in get_recorded_metrics_by_name()
