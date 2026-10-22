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


def send_translation_request(http_client: Client, text: str, language: LanguageName) -> None:
    """Ask the translate route to translate text and log the outcome.

    Failures are logged rather than raised, so one bad request doesn't end the run.
    """
    try:
        response = http_client.post(TRANSLATE_ROUTE, json={"text": text, "language": language})
    except HTTPError as error:
        logger.error("Request to translate %r into %s failed: %s", text, language, error)
        return
    if response.is_success:
        logger.info("Translated %r into %s: HTTP %d", text, language, response.status_code)
    else:
        logger.warning(
            "Translating %r into %s returned HTTP %d", text, language, response.status_code
        )


def run_synthetic_traffic(
    base_url: str,
    request_times: list[float],
    words: list[str],
    random_generator: Random,
) -> None:
    """Send one translation request at each planned time, counted from now."""
    start_time = monotonic()
    with Client(base_url=base_url, timeout=REQUEST_TIMEOUT_SECONDS) as http_client:
        for request_time in request_times:
            sleep(max(0.0, start_time + request_time - monotonic()))
            send_translation_request(
                http_client,
                random_generator.choice(words),
                random_generator.choice(TARGET_LANGUAGES),
            )


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
    arguments = parser.parse_args()
    if not 0 <= arguments.min_requests_per_hour <= arguments.max_requests_per_hour:
        parser.error("--min-requests-per-hour must be between 0 and --max-requests-per-hour")

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    # httpx logs every request at INFO, which would repeat send_translation_request's log line.
    logging.getLogger("httpx").setLevel(logging.WARNING)
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
    run_synthetic_traffic(
        arguments.base_url, request_times, load_words_to_translate(), random_generator
    )
    logger.info("Done")


if __name__ == "__main__":
    main()
