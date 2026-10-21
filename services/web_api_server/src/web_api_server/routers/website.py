"""Website route for the web API server.

It serves the translation page; main.py mounts WEBSITE_STATIC_DIR at /static for its CSS and JS.
"""

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

WEBSITE_DIR = Path(__file__).resolve().parent.parent / "website"
WEBSITE_STATIC_DIR = WEBSITE_DIR / "static"

# Serves the website's pages. They're left out of the API docs.
website_router = APIRouter(include_in_schema=False)


@website_router.get("/")
async def serve_home_page() -> FileResponse:
    """Serve the translation page."""
    return FileResponse(WEBSITE_DIR / "index.html")
