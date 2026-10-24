# translate-grpc

A translation service split into microservices. The project is a [uv workspace](https://docs.astral.sh/uv/concepts/projects/workspaces/): each part is its own package with its own `pyproject.toml` and dependencies.

- **gRPC server** (`services/translate_grpc/`): translates text with ChatGPT and listens on `localhost:50051`.
- **HTTP API** (`services/web_api_server/`): a FastAPI app that forwards requests to the gRPC server. It also serves the website (`web_api_server/website/`) at http://127.0.0.1:8000/.
- **Shared gRPC code** (`packages/translate_proto/`): the Python code generated from `protos/translate_proto/translator.proto`, plus the error and language helpers both services use.
- **Shared utilities** (`packages/utils/`): helpers used across the workspace, such as the `LanguageName` enum of supported languages.
- **Synthetic traffic** (`tools/synthetic_traffic/`): a script you run from your own machine to send randomly timed translation requests to the API. It isn't deployed.

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

Each service has its own image, built from the Dockerfile in its folder, and `compose.yaml` runs them together. An image contains only its service, the shared `translate_proto` and `utils` packages, and the libraries that service depends on. `compose.yaml` is also what Coolify deploys, so it doesn't publish any port; Coolify pulls the images CI pushes to GHCR rather than building them, so `compose.yaml` has no `build:` keys either. `compose.local.yaml` adds those and the port for running on your machine. With your `.env` file in place, run from the project root:

```bash
docker compose -f compose.yaml -f compose.local.yaml up --build
```

The API is published at http://127.0.0.1:8000/. The gRPC server is only reachable by the API, which finds it at `translate-grpc:50051` on the compose network (or on `TRANSLATE_GRPC_SERVER_PORT`, when set in `.env`). Stop everything with `docker compose down`.

#### Health checks

Both services have a Docker health check, so Docker and Coolify can tell a hung or crashed server from a healthy one. Each runs a command inside its container:

| Service          | Command                                    | What it checks                                              |
| ---------------- | ------------------------------------------ | ----------------------------------------------------------- |
| `translate-grpc` | `translate-grpc-healthcheck`               | The standard gRPC health service reports `SERVING`          |
| `web-api-server` | `curl --fail http://127.0.0.1:8000/health` | `GET /health` answers 200 (it doesn't call the gRPC server) |

curl can't speak the gRPC health protocol, so the gRPC server uses a Python command instead. The web API server's check calls port 8000, so if you change `WEB_API_SERVER_PORT`, change the port in its `healthcheck` in `compose.yaml` too.

Neither check sends a request to OpenAI. Docker runs them every 30s, and every 2s during the first 15s after a container starts. A container turns `unhealthy` after 3 failures in a row, and a check that takes longer than 5s counts as a failure. `web-api-server` only starts once `translate-grpc` is healthy. Check the status with:

```bash
docker compose ps
```

On every push to `main`, once the tests, type check and lint pass, CI rebuilds the images whose contents changed (the service's folder, `packages/`, `pyproject.toml`, `uv.lock` or `.dockerignore`) and pushes them to GHCR as `ghcr.io/feliceforgione/grpc2/<service>`, tagged `latest` and with the commit SHA.

### Monitoring

`compose.yaml` also runs Prometheus and Grafana, configured from the files in `monitoring/`. Prometheus scrapes the targets listed in `monitoring/prometheus/prometheus.yml` every 15 seconds and keeps 30 days of samples. Grafana starts with Prometheus already set up as its data source. Both keep their data in named volumes, so it survives restarts and redeploys.

Running locally, Grafana is at http://127.0.0.1:3300/ (log in as `admin` with the `GRAFANA_ADMIN_PASSWORD` from your `.env`) and Prometheus is at http://127.0.0.1:9090/. On the server, Prometheus stays private and Coolify's proxy routes a domain to Grafana's port 3300.

### Environment variables:

| Variable                        | Default           | Description                |
| ------------------------------- | ----------------- | -------------------------- |
| `TRANSLATE_GRPC_SERVER_ADDRESS` | `127.0.0.1:50051` | Address of the gRPC server |
| `WEB_API_SERVER_HOST`           | `127.0.0.1`       | Host the API binds to      |
| `WEB_API_SERVER_PORT`           | `8000`            | Port the API listens on    |

### Synthetic traffic

`uv run synthetic-traffic` sends translation requests to the API's `POST /api/translate/` route, the same route the website's form uses. Each hour it sends a random number of requests (0 to 5 by default) at random moments within the hour, each translating a random word from [`words.csv`](tools/synthetic_traffic/src/synthetic_traffic/words.csv) into a random language other than English. It logs each request's status and stops after the last one, logging how many requests it sent and how many succeeded. Every request is one OpenAI call, so keep the numbers small.

```bash
# 0-5 requests an hour for 4 hours, to the API on this machine
uv run synthetic-traffic

# Against the deployed site, 2-6 requests an hour for 1 hour
uv run synthetic-traffic --base-url https://your-domain --hours 1 --min-requests-per-hour 2 --max-requests-per-hour 6
```

The target defaults to `$SYNTHETIC_TRAFFIC_BASE_URL`, or `http://127.0.0.1:8000` when that isn't set. Keep the deployed domain out of the repo: pass it on the command line or set the variable in your shell. Add `--log-file` to also append the log to `synthetic_traffic.log` in the current directory, or `--log-file path/to/file.log` for another file. Run `uv run synthetic-traffic --help` for every option.

To leave it running in the background and follow the log, run these from the repo root, one at a time:

```bash
# Exactly 3 requests in 1 hour against the deployed site, logged to synthetic_traffic.log
nohup uv run synthetic-traffic --base-url https://your-domain --hours 1 --min-requests-per-hour 3 --max-requests-per-hour 3 --log-file > nohup.out 2>&1 &

# -F (not -f) waits for the log file to appear, since the script takes a moment to start
tail -F synthetic_traffic.log
```

The run stops by itself after its last request. Ctrl+C stops only `tail`. If the log never appears, `cat nohup.out` shows the error.

## Testing

Each service and package keeps its tests in its own `tests/` folder:

| Folder                           | What it tests                                                   |
| -------------------------------- | --------------------------------------------------------------- |
| `services/web_api_server/tests/` | FastAPI routes, called in-process with FastAPI's `TestClient`   |
| `services/translate_grpc/tests/` | The gRPC server, started in-process on a free port              |
| `packages/translate_proto/tests/`| The shared language mappings                                    |
| `tools/synthetic_traffic/tests/` | The synthetic traffic script's scheduling and requests          |

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

### Website tests

The translation page's script (`services/web_api_server/src/web_api_server/website/static/js/translate.js`) is tested with [Jest](https://jestjs.io/) in a simulated browser (jsdom). `fetch` is replaced with mocked server responses, so neither server needs to be running. The tests live in `services/web_api_server/tests/js/` and need Node.js 24:

```bash
cd services/web_api_server
npm install
npm test
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
