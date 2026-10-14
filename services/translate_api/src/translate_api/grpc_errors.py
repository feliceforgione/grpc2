"""Map failed gRPC calls errors to HTTP error responses."""

import logging

from fastapi import Request
from fastapi.responses import JSONResponse
from grpc import StatusCode
from grpc.aio import AioRpcError
from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_502_BAD_GATEWAY,
    HTTP_503_SERVICE_UNAVAILABLE,
    HTTP_504_GATEWAY_TIMEOUT,
)

# gRPC status codes that map to a specific HTTP status; anything else is a 502.
GRPC_ERROR_TO_HTTP_STATUS = {
    StatusCode.INVALID_ARGUMENT: HTTP_400_BAD_REQUEST,
    StatusCode.UNAVAILABLE: HTTP_503_SERVICE_UNAVAILABLE,
    StatusCode.DEADLINE_EXCEEDED: HTTP_504_GATEWAY_TIMEOUT,
}


async def handle_grpc_error_response(request: Request, grpc_error: AioRpcError) -> JSONResponse:
    """Exception handler that translates a failed gRPC call into an HTTP error response."""
    logging.warning(
        "gRPC call failed for %s: %s %s", request.url.path, grpc_error.code(), grpc_error.details()
    )
    http_status = GRPC_ERROR_TO_HTTP_STATUS.get(grpc_error.code(), HTTP_502_BAD_GATEWAY)
    # Only client errors carry the server's message; others may expose internal details.
    if http_status == HTTP_400_BAD_REQUEST:
        error_detail = grpc_error.details() or "Invalid request"
    else:
        error_detail = "Upstream service error"
    return JSONResponse(status_code=http_status, content={"detail": error_detail})
