import { readFileSync } from "node:fs";

import { afterEach, beforeEach, describe, expect, jest, test } from "@jest/globals";

import {
  describeErrorResponse,
  fetchSupportedLanguages,
  findPageElements,
  requestTranslation,
  startTranslatePage,
  submitTranslation,
  TRANSLATE_URL,
} from "../../src/web_api_server/website/static/js/translate.js";

const INDEX_HTML = readFileSync(
  new URL("../../src/web_api_server/website/index.html", import.meta.url),
  "utf8",
);
const VALID_TEXT = "hello";
const VALID_LANGUAGE = "italian";
const VALID_LANGUAGES = ["italian", "french", "spanish"];

// Build the object fetch resolves with; only the fields translate.js reads are set.
function buildMockResponse(status, body) {
  return { ok: status >= 200 && status < 300, status, json: async () => body };
}

function mockFetchResponses(...responses) {
  global.fetch = jest.fn();
  for (const response of responses) {
    global.fetch.mockResolvedValueOnce(response);
  }
}

beforeEach(() => {
  document.documentElement.innerHTML = INDEX_HTML;
});

afterEach(() => {
  delete global.fetch;
});

describe("describeErrorResponse", () => {
  test.each([
    [
      422,
      { detail: [{ loc: ["body", "text"], type: "string_too_short", msg: "too short" }] },
      "Enter some text to translate.",
    ], // empty text gets a hint instead of pydantic's message
    [
      422,
      { detail: [{ loc: ["body", "language"], type: "enum", msg: "bad enum" }] },
      "Choose a language from the list.",
    ], // a language outside LanguageName
    [
      422,
      { detail: [{ loc: ["body", "other"], type: "missing", msg: "Field required" }] },
      "other: Field required",
    ], // unexpected fields fall back to pydantic's message
    [422, null, "The request was invalid."], // no parsable body
    [
      400,
      { detail: "language must be set to a supported value" },
      "language must be set to a supported value",
    ], // the API only passes on the gRPC message for client errors
    [
      503,
      { detail: "Upstream service error" },
      "The translation service is unavailable right now. Please try again later.",
    ], // gRPC server is down
    [
      504,
      { detail: "Upstream service error" },
      "The translation took too long. Please try again.",
    ], // gRPC call timed out
    [
      502,
      { detail: "Upstream service error" },
      "Something went wrong on the server (HTTP 502). Please try again.",
    ], // any other server error gets a generic message with the status
    [
      400,
      null,
      "Something went wrong on the server (HTTP 400). Please try again.",
    ], // a 400 without a string detail has nothing useful to show
  ])("status %p with body %j describes %p", (status, body, expected) => {
    expect(describeErrorResponse(status, body)).toBe(expected);
  });
});

describe("fetchSupportedLanguages", () => {
  test("returns the languages from the languages route", async () => {
    mockFetchResponses(buildMockResponse(200, { languages: VALID_LANGUAGES }));

    await expect(fetchSupportedLanguages()).resolves.toEqual(VALID_LANGUAGES);
  });
});

describe("requestTranslation", () => {
  test("posts the text and language as JSON and returns the translated text", async () => {
    mockFetchResponses(buildMockResponse(200, { translated_text: "ciao" }));

    await expect(requestTranslation(VALID_TEXT, VALID_LANGUAGE)).resolves.toBe("ciao");
    expect(global.fetch).toHaveBeenCalledWith(TRANSLATE_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: VALID_TEXT, language: VALID_LANGUAGE }),
    });
  });

  test("rejects with a network message when the server can't be reached", async () => {
    global.fetch = jest.fn().mockRejectedValue(new TypeError("Failed to fetch"));

    await expect(requestTranslation(VALID_TEXT, VALID_LANGUAGE)).rejects.toThrow(
      "Could not reach the server. Check your connection and try again.",
    );
  });

  test("rejects with the status message when the error body isn't JSON", async () => {
    mockFetchResponses({
      ok: false,
      status: 502,
      json: async () => {
        throw new SyntaxError("Unexpected token <");
      },
    });

    await expect(requestTranslation(VALID_TEXT, VALID_LANGUAGE)).rejects.toThrow(
      "Something went wrong on the server (HTTP 502). Please try again.",
    );
  });
});

describe("translation page", () => {
  test("fills the language dropdown and enables the form once languages load", async () => {
    mockFetchResponses(buildMockResponse(200, { languages: VALID_LANGUAGES }));

    await startTranslatePage(document);

    const page = findPageElements(document);
    expect([...page.languageSelect.options].map((option) => [option.value, option.text])).toEqual(
      [
        ["italian", "Italian"],
        ["french", "French"],
        ["spanish", "Spanish"],
      ],
    );
    expect(page.languageSelect.disabled).toBe(false);
    expect(page.translateButton.disabled).toBe(false);
    expect(page.errorMessage.hidden).toBe(true);
  });

  test("shows an error and keeps the form disabled when languages fail to load", async () => {
    mockFetchResponses(buildMockResponse(500, { detail: "Internal Server Error" }));

    await startTranslatePage(document);

    const page = findPageElements(document);
    expect(page.errorMessage.hidden).toBe(false);
    expect(page.errorMessage.textContent).toBe(
      "Could not load languages. Something went wrong on the server (HTTP 500). Please try again.",
    );
    expect(page.translateButton.disabled).toBe(true);
  });

  test("shows the translation", async () => {
    mockFetchResponses(
      buildMockResponse(200, { languages: VALID_LANGUAGES }),
      buildMockResponse(200, { translated_text: "ciao" }),
    );
    await startTranslatePage(document);
    const page = findPageElements(document);
    page.textInput.value = VALID_TEXT;
    page.languageSelect.value = VALID_LANGUAGE;

    await submitTranslation(page);

    expect(page.translationOutput.value).toBe("ciao");
    expect(page.errorMessage.hidden).toBe(true);
    expect(page.translateButton.disabled).toBe(false);
  });

  test("shows the server's error and clears the old translation", async () => {
    mockFetchResponses(
      buildMockResponse(200, { languages: VALID_LANGUAGES }),
      buildMockResponse(503, { detail: "Upstream service error" }),
    );
    await startTranslatePage(document);
    const page = findPageElements(document);
    page.translationOutput.value = "stale translation";
    page.textInput.value = VALID_TEXT;

    await submitTranslation(page);

    expect(page.translationOutput.value).toBe("");
    expect(page.errorMessage.hidden).toBe(false);
    expect(page.errorMessage.textContent).toBe(
      "The translation service is unavailable right now. Please try again later.",
    );
    expect(page.translateButton.disabled).toBe(false);
  });

  test("marks the form busy while the translate request is in flight", async () => {
    mockFetchResponses(
      buildMockResponse(200, { languages: VALID_LANGUAGES }),
      buildMockResponse(200, { translated_text: "ciao" }),
    );
    await startTranslatePage(document);
    const page = findPageElements(document);
    page.textInput.value = VALID_TEXT;

    const translation = submitTranslation(page);

    expect(page.form.getAttribute("aria-busy")).toBe("true");
    expect(page.translateButton.disabled).toBe(true);
    await translation;
    expect(page.form.hasAttribute("aria-busy")).toBe(false);
  });

  test("submitting the form sends a translate request instead of reloading the page", async () => {
    mockFetchResponses(
      buildMockResponse(200, { languages: VALID_LANGUAGES }),
      buildMockResponse(200, { translated_text: "ciao" }),
    );
    await startTranslatePage(document);
    const page = findPageElements(document);
    page.textInput.value = VALID_TEXT;
    page.languageSelect.value = VALID_LANGUAGE;

    const submitEvent = new Event("submit", { cancelable: true });
    page.form.dispatchEvent(submitEvent);

    expect(submitEvent.defaultPrevented).toBe(true);
    expect(global.fetch).toHaveBeenLastCalledWith(TRANSLATE_URL, expect.anything());
  });
});
