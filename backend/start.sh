#!/bin/sh
set -e

echo "==> Running database migrations..."
# Try to run migrations. If alembic_version table doesn't exist yet (fresh DB
# where create_all ran instead of alembic), stamp the DB at head first so
# subsequent deploys apply incremental migrations correctly.
if alembic upgrade head; then
    echo "==> Migrations applied successfully."
else
    echo "WARNING: 'alembic upgrade head' failed. Attempting to stamp existing schema at head..."
    alembic stamp head || echo "WARNING: Stamp also failed — DB may have been initialized via create_all. Continuing..."
fi

echo "==> Starting Uvicorn server on port ${PORT:-8000}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --workers 1 --proxy-headers
