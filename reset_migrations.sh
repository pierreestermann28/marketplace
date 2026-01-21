#!/usr/bin/env bash
set -e

echo "🧹 Cleaning __pycache__ and .pyc files..."
find . -type d -name "__pycache__" -prune -exec rm -rf {} +
find . -type f -name "*.pyc" -delete

echo "🧹 Removing migration files (keeping __init__.py)..."
find . -path "*/migrations/*.py" \
  -not -name "__init__.py" \
  -delete

find . -path "*/migrations/*.pyc" -delete

echo "📦 Recreating migrations..."
python manage.py makemigrations


echo "✅ Done. Clean migration state."
