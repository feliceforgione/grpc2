from fastapi import APIRouter

translate_router = APIRouter(prefix="/api/translate", tags=["Translation"])


@translate_router.post("/")
async def translate() -> None:
    """Translate text into the requested language. Not implemented yet; does nothing."""
