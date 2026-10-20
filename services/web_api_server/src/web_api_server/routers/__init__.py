from web_api_server.routers.health import health_router
from web_api_server.routers.languages import languages_router
from web_api_server.routers.translate import translate_router
from web_api_server.routers.website import WEBSITE_STATIC_DIR, website_router

__all__ = [
    "WEBSITE_STATIC_DIR",
    "health_router",
    "languages_router",
    "translate_router",
    "website_router",
]
