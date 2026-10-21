"""Settings shared by the gRPC server and its health check command.

Kept apart from `server` so the health check can read them without importing
`translation`, which needs OPENAI_API_KEY.
"""

import os

TRANSLATE_GRPC_SERVER_PORT = int(os.environ.get("TRANSLATE_GRPC_SERVER_PORT", "50051"))
