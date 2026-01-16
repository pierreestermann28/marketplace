#!/bin/sh
set -e

POSTGRES_HOST=${POSTGRES_HOST:-postgres}
POSTGRES_PORT=${POSTGRES_PORT:-5432}
POSTGRES_USER=${POSTGRES_USER:-postgres}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-postgres}

REDIS_HOST=${REDIS_HOST:-redis}
REDIS_PORT=${REDIS_PORT:-6379}

echo "Waiting for Postgres at ${POSTGRES_HOST}:${POSTGRES_PORT}..."
until PGPASSWORD=$POSTGRES_PASSWORD pg_isready -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" >/dev/null 2>&1; do
  sleep 1
done

echo "Waiting for Redis at ${REDIS_HOST}:${REDIS_PORT}..."
until redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" ping >/dev/null 2>&1; do
  sleep 1
done

if [ "${SKIP_MIGRATE:-0}" = "1" ]; then
  echo "SKIP_MIGRATE=1, skipping migrations."
else
  echo "Applying migrations..."
  python manage.py migrate --noinput
fi

exec "$@"
