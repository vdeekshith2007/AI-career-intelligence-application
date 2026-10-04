#!/bin/sh
set -e

echo "==> Running database migrations..."
alembic upgrade head || echo "WARNING: Migrations failed or no migrations found, continuing..."

echo "==> Starting Uvicorn server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1 --proxy-headers
