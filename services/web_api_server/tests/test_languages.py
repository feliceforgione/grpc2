from fastapi.testclient import TestClient

from utils.language_name import LanguageName
from web_api_server.main import app

LANGUAGES_ROUTE_URL = "/api/languages"


def test_languages_route_returns_every_language_name_value() -> None:
    """`GET /api/languages` returns 200 with exactly the LanguageName values, in enum order."""
    response = TestClient(app).get(LANGUAGES_ROUTE_URL)

    assert response.status_code == 200
    assert response.json() == {"languages": [language.value for language in LanguageName]}

    # Check that value language is returned
    valid_language = "polish"
    assert LanguageName.POLISH in response.json()["languages"]
    assert valid_language in response.json()["languages"]
