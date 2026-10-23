# Build from the repo root, because the service needs the workspace's uv.lock
# and shared packages:
#   docker build -f services/translate_grpc/Dockerfile .

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
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-install-workspace --package translate-grpc

# Then install the service and the shared packages it uses. --no-editable
# copies them into .venv, so the runtime image needs nothing but .venv.
COPY packages/ packages/
COPY services/translate_grpc/ services/translate_grpc/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-editable --package translate-grpc


FROM python:3.13-slim-trixie

RUN useradd --system --no-create-home app
COPY --from=builder --chown=app:app /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"
USER app

EXPOSE 50051
CMD ["translate-grpc"]
