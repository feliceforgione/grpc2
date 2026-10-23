"""Open the gRPC channel used to call the translate gRPC server."""

import json

from grpc import StatusCode
from grpc.aio import Channel, insecure_channel

# Status codes the channel retries by itself before the call fails:
# - UNAVAILABLE: the server was down or the connection dropped before it answered.
# - RESOURCE_EXHAUSTED: the server was overloaded or rate limited; the backoff gives it room.
# tests/test_grpc_retries.py fails if one of these stops being retried
RETRYABLE_STATUS_CODES = [StatusCode.UNAVAILABLE, StatusCode.RESOURCE_EXHAUSTED]

# Counts the first attempt, so a call is retried at most MAX_ATTEMPTS - 1 times.
MAX_ATTEMPTS = 3

# The methods the retry policy applies to. The empty entry, {}, matches every method on the
# channel, so every call is retried. To retry only some methods, list them instead, e.g.
# {"service": "translator.v1.Translation", "method": "Translate"}; the service name must match
# the proto's package and service exactly, or the entry silently matches nothing.
METHOD_NAMES_TO_RETRY: list[dict[str, str]] = [{}]

GRPC_SERVICE_CONFIG = {
    "methodConfig": [
        {
            "name": METHOD_NAMES_TO_RETRY,
            "retryPolicy": {
                "maxAttempts": MAX_ATTEMPTS,
                "initialBackoff": "0.1s",
                "maxBackoff": "1s",
                "backoffMultiplier": 2,
                "retryableStatusCodes": [
                    status_code.name for status_code in RETRYABLE_STATUS_CODES
                ],
            },
        }
    ]
}


def open_translate_grpc_channel(server_address: str) -> Channel:
    """Open a translate gRPC channel that retries METHOD_NAMES_TO_RETRY on RETRYABLE_STATUS_CODES"""
    return insecure_channel(
        server_address, options=[("grpc.service_config", json.dumps(GRPC_SERVICE_CONFIG))]
    )
