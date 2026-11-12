from unittest.mock import patch

from grpc.aio import Channel
from grpc_health.v1.health_pb2 import HealthCheckRequest, HealthCheckResponse
from grpc_health.v1.health_pb2_grpc import HealthStub

from character_count_grpc.healthcheck import main
from utils.constants import CHARACTER_COUNT_GRPC_SERVER_PORT


async def test_health_check_reports_serving(character_count_grpc_channel: Channel) -> None:
    """The real server answers a `Health/Check` call with SERVING.

    Tests that the server registers the shared health service. utils' tests cover the
    service and the check itself.
    """
    response = await HealthStub(character_count_grpc_channel).Check(HealthCheckRequest())

    assert response.status == HealthCheckResponse.SERVING


def test_healthcheck_main_checks_the_character_count_server_port() -> None:
    """`main()`, which the container health check runs, checks this server's own port."""
    with patch(
        "character_count_grpc.healthcheck.run_grpc_health_check"
    ) as mock_run_grpc_health_check:
        main()

    mock_run_grpc_health_check.assert_called_once_with(CHARACTER_COUNT_GRPC_SERVER_PORT)
