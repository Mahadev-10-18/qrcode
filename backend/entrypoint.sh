#!/bin/sh
set -e

# Run database migrations
echo "Running database migrations..."
alembic upgrade head

# Start the application
exec uvicorn backend.main:app --host 0.0.0.0 --port "${PORT:-8000}"
