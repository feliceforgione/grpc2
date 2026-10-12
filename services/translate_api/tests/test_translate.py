from fastapi.testclient import TestClient

from translate_api.main import app

TRANSLATE_URL = "/api/translate/"

client = TestClient(app)


def test_translate_returns_success() -> None:
    response = client.post(TRANSLATE_URL)

    assert response.status_code == 200
