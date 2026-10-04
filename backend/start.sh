#!/bin/sh
set -e

echo "==> Running database migrations..."
alembic upgrade head || echo "WARNING: Migrations failed or no migrations found, continuing..."

echo "==> Starting Uvicorn server on port ${PORT:-8000}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --workers 1 --proxy-headers
