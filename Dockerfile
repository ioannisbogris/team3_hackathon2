# Pinned by digest so the base image can't change underneath us
FROM python:3.11.16-slim@sha256:da047cb8f9d1d98e5c070f5300ba9f7274e33b8fc0e5be5ed88740aed1b95ba9

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PATH="/app/.venv/bin:$PATH"

# Pinned uv version (matches the one used to generate uv.lock)
COPY --from=ghcr.io/astral-sh/uv:0.12.17 /uv /uvx /bin/

WORKDIR /app

# Install exactly what uv.lock specifies; --locked fails the build if the lock is stale
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --locked --no-dev --no-install-project

# Copy application source code and install the local package
COPY . .
RUN uv sync --locked --no-dev

EXPOSE 8000

CMD ["uvicorn", "src.team3_hackathon2.api:app", "--host", "0.0.0.0", "--port", "8000"]
