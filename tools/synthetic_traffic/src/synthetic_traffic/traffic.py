"""Send synthetic traffic to the web API server's translate route.

Each hour of the run gets a random number of requests, sent at random moments within
that hour, so the server sees a steady but jittered cadence. Every request translates
a random word from words.csv into a random language. Each request costs an OpenAI
call, so the defaults keep the volume low.
"""

import logging
import os
from argparse import ArgumentParser
from csv import DictReader
from pathlib import Path
from random import Random
from time import monotonic, sleep

from httpx import Client, HTTPError

from utils.language_name import LanguageName

DEFAULT_BASE_URL = os.environ.get("SYNTHETIC_TRAFFIC_BASE_URL", "http://127.0.0.1:8000")
TRANSLATE_ROUTE = "/api/translate/"

WORDS_TO_TRANSLATE_CSV_PATH = Path(__file__).parent / "words.csv"

SECONDS_PER_HOUR = 3600
REQUEST_TIMEOUT_SECONDS = 30.0

LOG_FORMAT = "%(asctime)s %(levelname)s %(message)s"
DEFAULT_LOG_FILE_PATH = Path("synthetic_traffic.log")

# The words are English, which is the translator's source language
TARGET_LANGUAGES = [language for language in LanguageName if language != LanguageName.ENGLISH]

logger = logging.getLogger(__name__)


def load_words_to_translate(
    words_to_translate_csv_path: Path = WORDS_TO_TRANSLATE_CSV_PATH,
) -> list[str]:
    """Read the `word` column of the words CSV."""
    with words_to_translate_csv_path.open(newline="") as words_file:
        return [row["word"] for row in DictReader(words_file)]


def create_request_times(
    hours: int,
    min_requests_per_hour: int,
    max_requests_per_hour: int,
    random_generator: Random,
) -> list[float]:
    """Pick when to send each request, in seconds from the start of the run, in order.

    Each hour gets between min_requests_per_hour and max_requests_per_hour requests
    (inclusive), each at a random moment within that hour.
    """
    request_times: list[float] = []
    for hour in range(hours):
        request_count = random_generator.randint(min_requests_per_hour, max_requests_per_hour)
        hour_start = hour * SECONDS_PER_HOUR
        request_times.extend(
            hour_start + random_generator.uniform(0, SECONDS_PER_HOUR) for _ in range(request_count)
        )
    return sorted(request_times)


def is_translation_request_successful(
    http_client: Client, text: str, language: LanguageName
) -> bool:
    """Ask the translate route to translate text, log the outcome and say whether it succeeded.

    Failures are logged rather than raised, so one bad request doesn't end the run.
    """
    try:
        response = http_client.post(TRANSLATE_ROUTE, json={"text": text, "language": language})
    except HTTPError as error:
        logger.error("Request to translate %r into %s failed: %s", text, language, error)
        return False
    if response.is_success:
        logger.info("Translated %r into %s: HTTP %d", text, language, response.status_code)
    else:
        logger.warning(
            "Translating %r into %s returned HTTP %d", text, language, response.status_code
        )
    return response.is_success


def configure_logging(log_file_path: Path | None) -> None:
    """Log to the terminal and, when log_file_path is given, append to that file too."""
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if log_file_path is not None:
        handlers.append(logging.FileHandler(log_file_path))
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT, handlers=handlers)
    # httpx logs every request at INFO, which would repeat our own per-request log line.
    logging.getLogger("httpx").setLevel(logging.WARNING)


def run_synthetic_traffic(
    base_url: str,
    request_times: list[float],
    words: list[str],
    random_generator: Random,
) -> int:
    """Send one translation request at each planned time, counted from now.

    Returns how many of the requests succeeded.
    """
    start_time = monotonic()
    successful_request_count = 0
    with Client(base_url=base_url, timeout=REQUEST_TIMEOUT_SECONDS) as http_client:
        for request_time in request_times:
            sleep(max(0.0, start_time + request_time - monotonic()))
            if is_translation_request_successful(
                http_client,
                random_generator.choice(words),
                random_generator.choice(TARGET_LANGUAGES),
            ):
                successful_request_count += 1
    return successful_request_count


def main() -> None:
    """Parse the command line, plan the requests and send them."""
    parser = ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help="web API server to send requests to (default: $SYNTHETIC_TRAFFIC_BASE_URL "
        "or %(default)s)",
    )
    parser.add_argument("--hours", type=int, default=4, help="how long to run (default: 4)")
    parser.add_argument(
        "--min-requests-per-hour",
        type=int,
        default=0,
        help="fewest requests in an hour (default: 0)",
    )
    parser.add_argument(
        "--max-requests-per-hour",
        type=int,
        default=5,
        help="most requests in an hour (default: 5)",
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        nargs="?",
        const=DEFAULT_LOG_FILE_PATH,
        help="also append the log to this file (default when the flag has no path: %(const)s)",
    )
    arguments = parser.parse_args()
    if not 0 <= arguments.min_requests_per_hour <= arguments.max_requests_per_hour:
        parser.error("--min-requests-per-hour must be between 0 and --max-requests-per-hour")

    configure_logging(arguments.log_file)
    random_generator = Random()
    request_times = create_request_times(
        arguments.hours,
        arguments.min_requests_per_hour,
        arguments.max_requests_per_hour,
        random_generator,
    )
    logger.info(
        "Sending %d requests to %s over %d hours",
        len(request_times),
        arguments.base_url,
        arguments.hours,
    )
    successful_request_count = run_synthetic_traffic(
        arguments.base_url, request_times, load_words_to_translate(), random_generator
    )
    logger.info(
        "Done: sent %d requests, %d succeeded", len(request_times), successful_request_count
    )


if __name__ == "__main__":
    main()
