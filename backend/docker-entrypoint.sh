#!/usr/bin/env bash
set -e
echo "==> Migrations Alembic"
alembic upgrade head
echo "==> Uvicorn sur le port 7860"
exec uvicorn app.main:app --host 0.0.0.0 --port 7860