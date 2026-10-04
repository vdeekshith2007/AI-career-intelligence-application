# ============================================================
# AI Career Intelligence — Production Backend Dockerfile
# ============================================================

# Multi-stage build for minimal image size and attack surface
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build dependencies (libpq-dev for asyncpg, gcc for chromadb native extensions)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages into isolated virtualenv
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
# Filter out test/dev dependencies for lean production build
RUN grep -v -E "pytest|ruff|mypy|black" requirements.txt > reqs-prod.txt && \
    pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r reqs-prod.txt

# ------------------------------------------------------------
# Final Runtime Stage
# ------------------------------------------------------------
FROM python:3.12-slim AS runner

WORKDIR /app

# Install curl for health checks and libgomp for ML packages (chromadb/sentence-transformers)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy virtualenv from builder stage
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=production \
    DEBUG=false

# Create unprivileged application user
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /bin/sh -M appuser

# Create persistent storage directories with correct permissions
RUN mkdir -p /app/data/uploads /app/data/chromadb && \
    chown -R appuser:appgroup /app

# Copy application source code
COPY --chown=appuser:appgroup alembic.ini .
COPY --chown=appuser:appgroup alembic ./alembic
COPY --chown=appuser:appgroup app ./app

# Copy startup script (runs migrations then starts server)
COPY --chown=root:root start.sh /app/start.sh
RUN chmod +x /app/start.sh

USER appuser

EXPOSE 8000

# Container healthcheck using liveness probe
# Extended start-period because HuggingFace model download takes time on cold start
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=5 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Production command: run migrations then start server
CMD ["/app/start.sh"]

