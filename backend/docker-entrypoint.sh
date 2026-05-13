#!/bin/sh
set -e

echo "Running database migrations..."
for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do
    if alembic upgrade head; then
        echo "Migrations complete."
        break
    fi
    echo "Migration attempt $i/15 failed — retrying in 10s..."
    sleep 10
    if [ "$i" = "15" ]; then
        echo "WARNING: All migration attempts failed — starting anyway"
    fi
done

echo "Starting uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --workers 2
