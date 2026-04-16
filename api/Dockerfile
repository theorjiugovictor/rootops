# ─── RootOps API ─────────────────────────────────────────────────
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_SYSTEM_PYTHON=1

WORKDIR /app

# System deps for asyncpg, gitpython, and sentence-transformers
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev git curl && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies securely via uv
COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv && \
    uv sync --frozen --no-cache --no-install-project

# Copy application code
COPY . .

# Non-root user with writable cache dir
RUN groupadd -r rootops && useradd -r -g rootops -m rootops \
    && mkdir -p /home/rootops/.cache \
    && chown -R rootops:rootops /app /home/rootops
USER rootops

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl --fail http://localhost:8000/health || exit 1

CMD ["uv", "run", "--no-project", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
