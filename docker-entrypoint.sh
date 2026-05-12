#!/bin/sh
set -e

echo "Running database migrations..."
alembic upgrade head || echo "WARNING: alembic upgrade failed — starting anyway"

echo "Starting uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --workers 2
