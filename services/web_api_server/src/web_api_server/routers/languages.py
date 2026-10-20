"""Languages route for the web API server.

It lists the languages the translate route accepts, read straight from LanguageName.
"""

from fastapi import APIRouter
from pydantic import BaseModel

from utils.language_name import LanguageName

languages_router = APIRouter(prefix="/api/languages", tags=["Languages"])


class LanguagesResponseBody(BaseModel):
    """JSON body returned by the languages route: every LanguageName value."""

    languages: list[LanguageName]


@languages_router.get("")
async def list_supported_languages() -> LanguagesResponseBody:
    """List the languages the translate route accepts."""
    return LanguagesResponseBody(languages=list(LanguageName))
