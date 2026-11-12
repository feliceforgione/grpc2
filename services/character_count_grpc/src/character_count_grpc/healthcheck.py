"""Command that Docker runs to check whether the character count gRPC server is up.

It calls the standard gRPC health service and exits with 0 when the server reports
SERVING, or 1 when it reports anything else or doesn't answer in time.
"""

from utils.constants import CHARACTER_COUNT_GRPC_SERVER_PORT
from utils.grpc_health import run_grpc_health_check


def main() -> None:
    """Check the server on this machine's CHARACTER_COUNT_GRPC_SERVER_PORT and exit 0 if serving."""
    run_grpc_health_check(CHARACTER_COUNT_GRPC_SERVER_PORT)


if __name__ == "__main__":
    main()
