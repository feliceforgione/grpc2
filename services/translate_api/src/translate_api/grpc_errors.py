"""Map failed gRPC calls to HTTP error responses."""

import logging
from collections.abc import Callable, Coroutine
from typing import Any

import grpc
import grpc.aio
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute

# gRPC status codes that map to a specific HTTP status; anything else is a 502.
GRPC_TO_HTTP_STATUS = {
    grpc.StatusCode.INVALID_ARGUMENT: status.HTTP_400_BAD_REQUEST,
    grpc.StatusCode.UNAVAILABLE: status.HTTP_503_SERVICE_UNAVAILABLE,
    grpc.StatusCode.DEADLINE_EXCEEDED: status.HTTP_504_GATEWAY_TIMEOUT,
}


def grpc_error_response(request: Request, grpc_error: grpc.aio.AioRpcError) -> JSONResponse:
    """Translate a failed gRPC call into an HTTP error response."""
    logging.warning(
        "gRPC call failed for %s: %s %s", request.url.path, grpc_error.code(), grpc_error.details()
    )
    http_status = GRPC_TO_HTTP_STATUS.get(grpc_error.code(), status.HTTP_502_BAD_GATEWAY)
    # Only client errors carry the server's message; others may expose internal details.
    if http_status == status.HTTP_400_BAD_REQUEST:
        error_detail = grpc_error.details() or "Invalid request"
    else:
        error_detail = "Upstream service error"
    return JSONResponse(status_code=http_status, content={"detail": error_detail})


class GrpcErrorRoute(APIRoute):
    """Route class that turns gRPC errors raised by its endpoint into HTTP error responses."""

    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        route_handler = super().get_route_handler()

        async def handler(request: Request) -> Response:
            try:
                return await route_handler(request)
            except grpc.aio.AioRpcError as grpc_error:
                return grpc_error_response(request, grpc_error)

        return handler
