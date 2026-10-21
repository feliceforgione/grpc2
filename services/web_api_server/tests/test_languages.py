from fastapi.testclient import TestClient

from utils.language_name import LanguageName
from web_api_server.main import app

LANGUAGES_ROUTE_URL = "/api/languages"


def test_languages_route_returns_every_language_name_value() -> None:
    """`GET /api/languages` returns 200 with exactly the LanguageName values, in enum order."""
    response = TestClient(app).get(LANGUAGES_ROUTE_URL)

    assert response.status_code == 200
    assert response.json() == {"languages": [language.value for language in LanguageName]}

    # LanguageName is similar to the Language (proto) with the proto returning integer values.
    # Ensure that the response is using the LanguageName StrEnum which are string values.
    assert LanguageName.POLISH.value == "polish"
