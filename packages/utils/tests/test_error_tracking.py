import os
from unittest.mock import patch

from utils.error_tracking import setup_error_tracking

MOCK_SERVICE_NAME = "foo"


def test_setup_error_tracking_sends_nothing_without_sentry_dsn() -> None:
    with (
        patch.dict(os.environ, {"SENTRY_DSN": ""}),
        patch("utils.error_tracking.sentry_sdk") as mock_sentry_sdk,
    ):
        setup_error_tracking(MOCK_SERVICE_NAME)

    mock_sentry_sdk.init.assert_not_called()


def test_setup_error_tracking_sends_to_sentry_dsn_tagged_with_service_name() -> None:
    sentry_dsn = "https://public-key@sentry.invalid/1"

    with (
        patch.dict(os.environ, {"SENTRY_DSN": sentry_dsn}),
        patch("utils.error_tracking.sentry_sdk") as mock_sentry_sdk,
    ):
        setup_error_tracking(MOCK_SERVICE_NAME)

    assert mock_sentry_sdk.init.call_args.kwargs["dsn"] == sentry_dsn
    mock_sentry_sdk.set_tag.assert_called_once_with("service", MOCK_SERVICE_NAME)
