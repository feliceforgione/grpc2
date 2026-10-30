"""FastAPI app for the web API server."""

import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from grpc.aio import AioRpcError
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from translate_proto.translator_pb2_grpc import TranslationStub
from utils.constants import LOOPBACK_IPV4, TRANSLATE_GRPC_SERVER_PORT
from utils.error_tracking import setup_error_tracking, tag_request_errors_with_trace
from utils.telemetry import setup_telemetry
from web_api_server.grpc_channel import open_translate_grpc_channel
from web_api_server.grpc_errors import handle_grpc_error_response
from web_api_server.routers import (
    WEBSITE_STATIC_DIR,
    health_router,
    languages_router,
    translate_router,
    website_router,
)

TRANSLATE_GRPC_SERVER_ADDRESS = os.environ.get(
    "TRANSLATE_GRPC_SERVER_ADDRESS", f"{LOOPBACK_IPV4}:{TRANSLATE_GRPC_SERVER_PORT}"
)
WEB_API_SERVER_HOST = os.environ.get("WEB_API_SERVER_HOST", LOOPBACK_IPV4)
WEB_API_SERVER_PORT = int(os.environ.get("WEB_API_SERVER_PORT", "8000"))


@asynccontextmanager
async def app_lifespan(fastapi_app: FastAPI) -> AsyncGenerator[None]:
    """Open one gRPC channel for the app's lifetime and share it across requests."""
    async with open_translate_grpc_channel(TRANSLATE_GRPC_SERVER_ADDRESS) as grpc_channel:
        fastapi_app.state.translate_grpc_client = TranslationStub(grpc_channel)  # type: ignore[no-untyped-call]
        yield


app = FastAPI(
    title="Translate API",
    lifespan=app_lifespan,
    exception_handlers={AioRpcError: handle_grpc_error_response},
)
app.include_router(health_router)
app.include_router(languages_router)
app.include_router(translate_router)
app.include_router(website_router)
app.mount("/static", StaticFiles(directory=WEBSITE_STATIC_DIR), name="static")
# Use the stable HTTP semantic conventions instead of the old default ones. Their request
# duration metric, http.server.request.duration, is in seconds and labelled with the route
# template, whereas the old http.server.duration labels each request with its raw path, which
# would make every static file and every unknown URL a separate Prometheus series. The
# instrumentation reads this once, in instrument_app(), so it's set here rather than in
# compose.yaml, which keeps the tests and a local run on the same conventions.
os.environ.setdefault("OTEL_SEMCONV_STABILITY_OPT_IN", "http")
# Record a span for each request. The spans go nowhere until main() calls setup_telemetry().
# Skipping the ASGI receive/send spans leaves one span per request instead of three or more.
# excluded_urls is a regex searched in the request's full URL, without the query string; it
# leaves out Docker's health checks so they don't add a span every 30s. The hook tags the errors
# Sentry captures during a request with that request's trace.
FastAPIInstrumentor.instrument_app(
    app,
    excluded_urls=f"{health_router.prefix}$",
    exclude_spans=["receive", "send"],
    server_request_hook=tag_request_errors_with_trace,
)


def main() -> None:
    """Run the app with uvicorn on WEB_API_SERVER_HOST and WEB_API_SERVER_PORT."""
    logging.basicConfig(level=logging.INFO)
    setup_telemetry("web-api-server")
    setup_error_tracking("web-api-server")
    uvicorn.run(app, host=WEB_API_SERVER_HOST, port=WEB_API_SERVER_PORT)


if __name__ == "__main__":
    main()
