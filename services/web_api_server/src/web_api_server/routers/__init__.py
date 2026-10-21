from web_api_server.routers.health import health_router
from web_api_server.routers.languages import languages_router
from web_api_server.routers.translate import translate_router

__all__ = ["health_router", "languages_router", "translate_router"]
