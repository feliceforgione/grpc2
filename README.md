# translate-grpc

A translation service split into microservices. The project is a [uv workspace](https://docs.astral.sh/uv/concepts/projects/workspaces/): each part is its own package with its own `pyproject.toml` and dependencies.

- **gRPC server** (`services/translate_grpc/`): translates text with ChatGPT and listens on `localhost:50051`.
- **HTTP API** (`services/web_api_server/`): a FastAPI app that forwards requests to the gRPC server. It also serves the website (`web_api_server/website/`) at http://127.0.0.1:8000/.
- **Shared gRPC code** (`packages/translate_proto/`): the Python code generated from `protos/translate_proto/translator.proto`, plus the error and language helpers both services use.
- **Shared utilities** (`packages/utils/`): helpers used across the workspace, such as the `LanguageName` enum of supported languages.

![The translation website translating "What is for dinner?" into French](screenshot.png)

### Installation

1. Install the dependencies, including the dev tools used to regenerate gRPC code:

   ```bash
   uv sync
   ```

   This creates a `.venv/` folder in the project and installs every workspace package, with everything listed in `uv.lock`, into it.

### The `.env` file

The gRPC server translates with ChatGPT, so it needs an OpenAI API key. Copy the sample file [`.env.example`](.env.example) to `.env` in the project root:

```bash
cp .env.example .env
```

Then open `.env` and replace the placeholder with your key, which you can get at https://platform.openai.com/api-keys:

### Running

Use two terminals, both opened in the project root:

```bash
# Terminal 1: the gRPC server
uv run translate-grpc
```

```bash
# Terminal 2: the HTTP API and website
uv run web-api-server
```

While working on the API, you can run it with auto-reload instead, so it restarts whenever you save a change:

```bash
uv run uvicorn web_api_server.main:app --reload
```

Then open http://127.0.0.1:8000/ to use the website. FastAPI also serves API documentation generated from the code:

- http://127.0.0.1:8000/docs: interactive docs (Swagger UI), where you can send requests to each endpoint
- http://127.0.0.1:8000/redoc: read-only reference docs (ReDoc)

To check that the API is up, call its health route. It returns `{"status": "ok"}` without calling the gRPC server, so it answers even when the gRPC server is down:

```bash
curl http://127.0.0.1:8000/health
```

### Running with Docker

Each service has its own image, built from the Dockerfile in its folder, and `compose.yaml` runs them together. An image contains only its service, the shared `translate_proto` and `utils` packages, and the libraries that service depends on. With your `.env` file in place, run from the project root:

```bash
docker compose up --build
```

The API is published at http://127.0.0.1:8000/. The gRPC server is only reachable by the API, which finds it at `translate-grpc:50051` on the compose network. Stop everything with `docker compose down`.

### Environment variables:

| Variable                        | Default           | Description                |
| ------------------------------- | ----------------- | -------------------------- |
| `TRANSLATE_GRPC_SERVER_ADDRESS` | `localhost:50051` | Address of the gRPC server |
| `WEB_API_SERVER_HOST`           | `127.0.0.1`       | Host the API binds to      |
| `WEB_API_SERVER_PORT`           | `8000`            | Port the API listens on    |

## Testing

Each service and package keeps its tests in its own `tests/` folder:

| Folder                           | What it tests                                                   |
| -------------------------------- | --------------------------------------------------------------- |
| `services/web_api_server/tests/` | FastAPI routes, called in-process with FastAPI's `TestClient`   |
| `services/translate_grpc/tests/` | The gRPC server, started in-process on a free port              |
| `packages/translate_proto/tests/`| The shared language mappings                                    |

By default the ChatGPT translator is replaced with a fake, so the tests run offline and need no API key:

```bash
# Run every test
uv run pytest -v

# Run one service's tests
uv run pytest services/web_api_server
uv run pytest services/translate_grpc
```

One test, marked `live`, calls the real OpenAI API to translate "Hello" into Italian. It is skipped by default and needs an `OPENAI_API_KEY` in `.env`:

```bash
# Run only the live test
uv run pytest -m live

# Run every test, live included
uv run pytest -m "" -v
```

## Type checking

The whole workspace (packages, services and tests) is checked with [mypy](https://mypy.readthedocs.io/) in strict mode. The settings live in the root `pyproject.toml`. Run from the project root:

```bash
uv run poe typecheck
```

Running `uv run mypy` does the same thing. The generated `translator_pb2*.py` files are excluded from error reporting.

## Linting and formatting

The workspace is linted and formatted with [Ruff](https://docs.astral.sh/ruff/). The settings live in the root `pyproject.toml`, and the generated `translator_pb2*` files are excluded. Run from the project root:

```bash
# Check for lint errors
uv run poe lint

# Format the code
uv run poe format
```

`uv run ruff check --fix` fixes lint errors that Ruff can fix on its own, such as unsorted imports. CI runs `ruff check` and `ruff format --check`, and fails if any file has lint errors or isn't formatted.

## Pre-commit hook

A [pre-commit](https://pre-commit.com/) hook runs the same checks as CI (`ruff check`, `ruff format --check`, `mypy` and `pytest`) before every commit, and blocks the commit if any of them fail. The hooks live in `.pre-commit-config.yaml`. Install the hook once after cloning:

```bash
uv run pre-commit install
```

To run the checks without committing, use `uv run pre-commit run --all-files`. To skip them for a single commit, use `git commit --no-verify`.

## Generating gRPC code

The service definition lives in `protos/translate_proto/translator.proto`. After editing it, regenerate the Python stubs (`translator_pb2.py`, `translator_pb2.pyi`, `translator_pb2_grpc.py` in `packages/translate_proto/src/translate_proto/`):

```bash
uv run poe proto
```
