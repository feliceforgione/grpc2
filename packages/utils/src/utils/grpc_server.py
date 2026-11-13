"""Creates the gRPC servers, so every service traces its RPCs the same way."""

from grpc.aio import Server, server
from opentelemetry.instrumentation.grpc import aio_server_interceptor
from opentelemetry.instrumentation.grpc.filters import health_check, negate


def create_grpc_server() -> Server:
    """Create a server that records a span for each RPC, except the health checks."""
    tracing_interceptor = aio_server_interceptor(  # type: ignore[no-untyped-call]
        filter_=negate(health_check())
    )
    return server(interceptors=[tracing_interceptor])
