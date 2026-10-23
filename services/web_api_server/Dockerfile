# Build from the repo root, because the service needs the workspace's uv.lock
# and shared packages:
#   docker build -f services/web_api_server/Dockerfile .

FROM ghcr.io/astral-sh/uv:0.13.2-python3.13-trixie-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app

# Install the third-party dependencies first, so this layer is reused until
# uv.lock or a pyproject.toml changes. uv needs every workspace member's
# pyproject.toml to check the lock file.
COPY pyproject.toml uv.lock ./
COPY packages/translate_proto/pyproject.toml packages/translate_proto/
COPY packages/utils/pyproject.toml packages/utils/
COPY services/translate_grpc/pyproject.toml services/translate_grpc/
COPY services/web_api_server/pyproject.toml services/web_api_server/
COPY tools/synthetic_traffic/pyproject.toml tools/synthetic_traffic/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-install-workspace --package web-api-server

# Then install the service and the shared packages it uses. --no-editable
# copies them into .venv, so the runtime image needs nothing but .venv.
COPY packages/ packages/
COPY services/web_api_server/ services/web_api_server/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-editable --package web-api-server


FROM python:3.13-slim-trixie

RUN useradd --system --no-create-home app
COPY --from=builder --chown=app:app /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"
USER app

# Listen on every interface, so the proxy in front of the container can reach it.
ENV WEB_API_SERVER_HOST=0.0.0.0 \
    WEB_API_SERVER_PORT=8000
EXPOSE 8000
CMD ["web-api-server"]
