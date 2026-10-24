"""Constants and settings shared by the services and their tests.

Settings are read from the environment, or from a `.env` file when one exists,
and fall back to the defaults below.
"""

import os

from dotenv import load_dotenv

load_dotenv()

LOOPBACK_IPV4 = "127.0.0.1"
TRANSLATE_GRPC_SERVER_PORT = int(os.environ.get("TRANSLATE_GRPC_SERVER_PORT", "50051"))
