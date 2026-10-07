# translate-grpc

A translation service split into microservices. The project is a [uv workspace](https://docs.astral.sh/uv/concepts/projects/workspaces/): each part is its own package with its own `pyproject.toml` and dependencies.

- **gRPC server** (`services/translate_grpc/`): translates text with ChatGPT and listens on `localhost:50051`.
- **HTTP API** (`services/translate_api/`): a FastAPI app that forwards requests to the gRPC server. It also serves the website (`translate_api/website/`) at http://127.0.0.1:8000/.
- **Shared gRPC code** (`packages/translate_proto/`): the Python code generated from `protos/translate_proto/translator.proto`, plus the error and language helpers both services use.

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
uv run translate-api
```

Then open http://127.0.0.1:8000/ to use the website, or http://127.0.0.1:8000/docs for the interactive API docs.

### Running with Docker

Each service has its own image, built from the Dockerfile in its folder, and `compose.yaml` runs them together. An image contains only its service, the shared `translate_proto` package, and the libraries that service depends on. With your `.env` file in place, run from the project root:

```bash
docker compose up --build
```

The API is published at http://127.0.0.1:8000/. The gRPC server is only reachable by the API, which finds it at `translate-grpc:50051` on the compose network. Stop everything with `docker compose down`.

### Environment variables:

| Variable                | Default           | Description                |
| ----------------------- | ----------------- | -------------------------- |
| `TRANSLATE_GRPC_TARGET` | `localhost:50051` | Address of the gRPC server |
| `TRANSLATE_API_HOST`    | `127.0.0.1`       | Host the API binds to      |
| `TRANSLATE_API_PORT`    | `8000`            | Port the API listens on    |

## Testing

The tests in `tests/` start the gRPC server in-process on a free port and call it through a real gRPC client. By default the ChatGPT translator is replaced with a fake, so the tests run offline and need no API key:

```bash
uv run pytest -v
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

## Generating gRPC code

The service definition lives in `protos/translate_proto/translator.proto`. After editing it, regenerate the Python stubs (`translator_pb2.py`, `translator_pb2.pyi`, `translator_pb2_grpc.py` in `packages/translate_proto/src/translate_proto/`):

```bash
uv run poe proto
```
