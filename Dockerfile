FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Copy uv binaries
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Leverage layer caching for dependencies
COPY pyproject.toml uv.lock ./
RUN uv pip install --system --no-cache -r pyproject.toml

# Copy application source code
COPY . .

# Install the local package
RUN uv pip install --system --no-cache .

EXPOSE 8000

CMD ["uvicorn", "src.team3_hackathon2.api:app", "--host", "0.0.0.0", "--port", "8000"]