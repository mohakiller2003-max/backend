#!/bin/sh
set -e

echo "Running Alembic migrations..."
alembic upgrade head

echo "Starting Skinouva API..."
exec gunicorn app.main:app \
  -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --workers 2 \
  --timeout 30 \
  --access-logfile - \
  --error-logfile -
