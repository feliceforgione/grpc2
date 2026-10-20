import pytest
from fastapi.testclient import TestClient

from web_api_server.main import app

HOME_PAGE_URL = "/"


def test_home_page_serves_the_translation_page() -> None:
    """`GET /` returns the HTML page with the form elements the page script looks up."""
    response = TestClient(app).get(HOME_PAGE_URL)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    for element_id in (
        "translate-form",
        "text-input",
        "language-select",
        "translate-button",
        "translation-output",
        "error-message",
    ):
        assert f'id="{element_id}"' in response.text


@pytest.mark.parametrize(
    ("url", "content_type"),
    [
        ("/static/css/style.css", "text/css"),  # linked from index.html
        ("/static/js/translate.js", "text/javascript"),  # loaded by index.html as a module
    ],
)
def test_static_files_linked_from_home_page_are_served(url: str, content_type: str) -> None:
    """The CSS and JS that index.html links to are served from /static."""
    response = TestClient(app).get(url)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith(content_type)


def test_home_page_is_left_out_of_api_docs() -> None:
    """The website route isn't part of the API, so the OpenAPI schema doesn't list it."""
    response = TestClient(app).get("/openapi.json")

    assert HOME_PAGE_URL not in response.json()["paths"]
