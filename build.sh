#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# Render build script for FieldFlow (SQLite / demo mode)
# ─────────────────────────────────────────────────────────────
set -o errexit   # abort on any error

pip install --upgrade pip
pip install -r requirements.txt

# Collect static files (WhiteNoise will serve them)
python manage.py collectstatic --no-input

# Run database migrations (creates db.sqlite3 if it doesn't exist)
python manage.py migrate --no-input
