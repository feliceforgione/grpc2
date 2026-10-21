// Logic for the translation page. The functions are exported so Jest can test them
// against mocked server responses; the page itself calls startTranslatePage on load.

export const LANGUAGES_URL = "/api/languages";
export const TRANSLATE_URL = "/api/translate/";

// Messages for HTTP statuses whose response detail isn't meant for users.
const SERVER_ERROR_MESSAGES = {
  503: "The translation service is unavailable right now. Please try again later.",
  504: "The translation took too long. Please try again.",
};
const NETWORK_ERROR_MESSAGE = "Could not reach the server. Check your connection and try again.";

// Raised for any failed request; message is ready to show to the user.
export class RequestFailedError extends Error {}

export function formatLanguageLabel(language) {
  return language.charAt(0).toUpperCase() + language.slice(1);
}

export function formatElapsedTime(milliseconds) {
  if (milliseconds < 1000) {
    return `${Math.round(milliseconds)} ms`;
  }
  return `${(milliseconds / 1000).toFixed(2)} s`;
}

// Turn FastAPI's 422 detail (a list of pydantic errors) into one readable sentence.
export function describeValidationErrors(detail) {
  if (!Array.isArray(detail) || detail.length === 0) {
    return "The request was invalid.";
  }
  return detail
    .map((error) => {
      const field = error.loc?.at(-1);
      if (field === "text" && error.type === "string_too_short") {
        return "Enter some text to translate.";
      }
      if (field === "language") {
        return "Choose a language from the list.";
      }
      return field ? `${field}: ${error.msg}` : error.msg;
    })
    .join(" ");
}

export function describeErrorResponse(status, body) {
  if (status === 422) {
    return describeValidationErrors(body?.detail);
  }
  if (status === 400 && typeof body?.detail === "string") {
    return body.detail;
  }
  return (
    SERVER_ERROR_MESSAGES[status] ??
    `Something went wrong on the server (HTTP ${status}). Please try again.`
  );
}

// Fetch a URL and return its JSON body, or throw RequestFailedError with a user-facing message.
async function fetchJson(url, options) {
  let response;
  try {
    response = await fetch(url, options);
  } catch {
    throw new RequestFailedError(NETWORK_ERROR_MESSAGE);
  }
  // Error responses from a proxy may not be JSON, so a body that won't parse is treated as empty.
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    throw new RequestFailedError(describeErrorResponse(response.status, body));
  }
  return body;
}

export async function fetchSupportedLanguages() {
  const body = await fetchJson(LANGUAGES_URL);
  return body.languages;
}

export async function requestTranslation(text, language) {
  const body = await fetchJson(TRANSLATE_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, language }),
  });
  return body.translated_text;
}

function showError(page, message) {
  page.errorMessage.textContent = message;
  page.errorMessage.hidden = false;
}

function clearError(page) {
  page.errorMessage.textContent = "";
  page.errorMessage.hidden = true;
}

export async function loadLanguageOptions(page) {
  try {
    const languages = await fetchSupportedLanguages();
    page.languageSelect.replaceChildren(
      ...languages.map((language) => new Option(formatLanguageLabel(language), language)),
    );
    page.languageSelect.disabled = false;
    page.translateButton.disabled = false;
  } catch (error) {
    page.languageSelect.replaceChildren(new Option("Languages unavailable", ""));
    showError(page, `Could not load languages. ${error.message}`);
  }
}

export async function submitTranslation(page) {
  clearError(page);
  page.translationOutput.value = "";
  page.elapsedTime.textContent = "Translating…";
  page.translateButton.disabled = true;
  page.form.setAttribute("aria-busy", "true");
  const startTime = performance.now();
  try {
    page.translationOutput.value = await requestTranslation(
      page.textInput.value,
      page.languageSelect.value,
    );
    page.elapsedTime.textContent = `Completed in ${formatElapsedTime(performance.now() - startTime)}`;
  } catch (error) {
    showError(page, error.message);
    page.elapsedTime.textContent = `Failed after ${formatElapsedTime(performance.now() - startTime)}`;
  } finally {
    page.translateButton.disabled = false;
    page.form.removeAttribute("aria-busy");
  }
}

export function findPageElements(document) {
  return {
    form: document.getElementById("translate-form"),
    textInput: document.getElementById("text-input"),
    languageSelect: document.getElementById("language-select"),
    translateButton: document.getElementById("translate-button"),
    translationOutput: document.getElementById("translation-output"),
    errorMessage: document.getElementById("error-message"),
    elapsedTime: document.getElementById("elapsed-time"),
  };
}

export function startTranslatePage(document) {
  const page = findPageElements(document);
  page.form.addEventListener("submit", (event) => {
    event.preventDefault();
    submitTranslation(page);
  });
  return loadLanguageOptions(page);
}

// Jest imports this module without a page to run on, so only start when the form exists.
if (typeof document !== "undefined" && document.getElementById("translate-form")) {
  startTranslatePage(document);
}
