"""Health check route for the web API server.

It reports only whether this server is up and never calls the gRPC servers behind it.
"""

from fastapi import APIRouter
from pydantic import BaseModel

health_router = APIRouter(prefix="/health", tags=["Health"])


class HealthResponseBody(BaseModel):
    """JSON body returned by the health route; status is "ok" while the server is up."""

    status: str


@health_router.get("")
async def check_web_api_server_health() -> HealthResponseBody:
    """Report that the web API server is up."""
    return HealthResponseBody(status="ok")
