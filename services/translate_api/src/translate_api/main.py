import logging
import os

import uvicorn
from fastapi import FastAPI

from translate_api.routers import translate_router

API_HOST = os.environ.get("TRANSLATE_API_HOST", "127.0.0.1")
API_PORT = int(os.environ.get("TRANSLATE_API_PORT", "8000"))


app = FastAPI(title="Translate API")
app.include_router(translate_router)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host=API_HOST, port=API_PORT)


if __name__ == "__main__":
    main()
