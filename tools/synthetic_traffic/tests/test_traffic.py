import logging
from pathlib import Path
from random import Random
from unittest.mock import Mock, call, patch

import pytest
from httpx import ConnectError

from synthetic_traffic.traffic import (
    SECONDS_PER_HOUR,
    TARGET_LANGUAGES,
    TRANSLATE_ROUTE,
    configure_logging,
    create_request_times,
    is_translation_request_successful,
    run_synthetic_traffic,
)
from utils.language_name import LanguageName

VALID_TEXT = "hello"
VALID_LANGUAGE = LanguageName.ITALIAN
VALID_BASE_URL = "http://127.0.0.1:8000"


def test_target_languages_exclude_english() -> None:
    """The words are already English, so English is never a target."""
    assert LanguageName.ENGLISH not in TARGET_LANGUAGES


@pytest.mark.parametrize(
    ("min_requests_per_hour", "max_requests_per_hour"),
    [
        (0, 5),  # the default range
        (3, 3),  # min equals max, so every hour has exactly 3
        (0, 0),  # no requests at all
    ],
)
def test_plan_request_times_spreads_requests_within_each_hour(
    min_requests_per_hour: int, max_requests_per_hour: int
) -> None:
    """Each hour gets a request count within the range, at times inside that hour, in order."""
    num_hours_to_test = 4
    request_times = create_request_times(
        num_hours_to_test, min_requests_per_hour, max_requests_per_hour, Random(0)
    )

    assert request_times == sorted(request_times)
    for hour in range(num_hours_to_test):
        hour_start = hour * SECONDS_PER_HOUR
        requests_in_hour = [
            request_time
            for request_time in request_times
            if hour_start <= request_time < hour_start + SECONDS_PER_HOUR
        ]
        assert min_requests_per_hour <= len(requests_in_hour) <= max_requests_per_hour
    assert all(
        0 <= request_time < num_hours_to_test * SECONDS_PER_HOUR for request_time in request_times
    )


def test_is_translation_request_successful_posts_text_and_language() -> None:
    """The request body matches what the translate route expects."""
    mock_http_client = Mock()
    mock_http_client.post.return_value = Mock(is_success=True, status_code=200)

    assert is_translation_request_successful(mock_http_client, VALID_TEXT, VALID_LANGUAGE)

    mock_http_client.post.assert_called_once_with(
        TRANSLATE_ROUTE, json={"text": VALID_TEXT, "language": VALID_LANGUAGE}
    )


def test_is_translation_request_successful_logs_connection_errors_instead_of_raising(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A failed request is logged, so the run carries on with the next one."""
    mock_http_client = Mock()
    mock_http_client.post.side_effect = ConnectError("mock connection error")

    assert not is_translation_request_successful(mock_http_client, VALID_TEXT, VALID_LANGUAGE)

    assert "mock connection error" in caplog.text


def test_is_translation_request_successful_logs_error_status_codes(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A non-2xx response is logged as a warning with its status code."""
    mock_http_client = Mock()
    mock_http_client.post.return_value = Mock(is_success=False, status_code=503)

    assert not is_translation_request_successful(mock_http_client, VALID_TEXT, VALID_LANGUAGE)

    assert "HTTP 503" in caplog.text


def test_run_synthetic_traffic_waits_until_each_request_time() -> None:
    """Each request is sent after sleeping until its planned time, counted from the start."""
    with (
        patch("synthetic_traffic.traffic.Client") as mock_client,
        patch("synthetic_traffic.traffic.sleep") as mock_sleep,
        patch("synthetic_traffic.traffic.monotonic") as mock_monotonic,
    ):
        mock_monotonic.return_value = 100.0
        mock_http_client = mock_client.return_value.__enter__.return_value
        mock_http_client.post.return_value = Mock(is_success=True, status_code=200)

        successful_request_count = run_synthetic_traffic(
            VALID_BASE_URL, [10.0, 30.0], [VALID_TEXT], Random(0)
        )

    assert successful_request_count == 2
    mock_client.assert_called_once()
    assert mock_client.call_args.kwargs["base_url"] == VALID_BASE_URL
    assert mock_sleep.call_args_list == [call(10.0), call(30.0)]
    assert mock_http_client.post.call_count == 2
    sent_body = mock_http_client.post.call_args.kwargs["json"]
    assert sent_body["text"] == VALID_TEXT
    assert sent_body["language"] in TARGET_LANGUAGES


def test_run_synthetic_traffic_counts_only_successful_requests() -> None:
    """Requests that get an error status are sent but not counted as successful."""
    with (
        patch("synthetic_traffic.traffic.Client") as mock_client,
        patch("synthetic_traffic.traffic.sleep"),
    ):
        mock_http_client = mock_client.return_value.__enter__.return_value
        mock_http_client.post.return_value = Mock(is_success=False, status_code=503)

        successful_request_count = run_synthetic_traffic(
            VALID_BASE_URL, [10.0, 30.0], [VALID_TEXT], Random(0)
        )

    assert mock_http_client.post.call_count == 2
    assert successful_request_count == 0


def test_configure_logging_appends_to_the_log_file(tmp_path: Path) -> None:
    """With a log file path, log lines are written to that file as well as the terminal."""
    log_file_path = tmp_path / "synthetic_traffic.log"
    logger = logging.getLogger()
    original_handlers = logger.handlers[:]
    logger.handlers.clear()

    expected_log_line = "mock log line"
    try:
        configure_logging(log_file_path)
        logging.getLogger("synthetic_traffic.traffic").info(expected_log_line)
        for handler in logger.handlers:
            handler.flush()
    finally:
        for handler in logger.handlers:
            handler.close()
        logger.handlers[:] = original_handlers

    assert expected_log_line in log_file_path.read_text()
