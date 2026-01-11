# StillUseful — Dockerized development

1 upload → IA → DetectedItem → swipe → listing, with Django + Celery + Redis + Tailwind in Docker.

## Quick start

1. Copy the env template:
   ```bash
   cp .env.example .env
   ```
2. Build & start everything (web, Celery worker, Tailwind watch, Postgres, Redis, Flower):
   ```bash
   docker compose up --build
   ```
   The entrypoint waits for Postgres/Redis and applies migrations before running the service command.

## Useful commands

- Run migrations manually (entrypoint already runs them, but this is handy when you change migrations):
  ```bash
  docker compose exec web python manage.py migrate
  ```
- Create a superuser:
  ```bash
  docker compose exec web python manage.py createsuperuser
  ```
- Open a Django shell:
  ```bash
  docker compose exec web python manage.py shell
  ```
- Tailwind/watch logs are streamed via the `tailwind` service. The `vendor` npm script runs automatically before `tailwind:watch`.
- Flower monitoring is available at http://localhost:5555/ (celery -A `stillusefull` is the module reference).

## Notes

- The `web`, `worker`, and `flower` services share the same Python image (`python:3.11-slim` with Node/npm installed) and reuse `/app` via a bind mount for live reload.
- Tailwind writes to `static/css/app.css` (same as the existing Tailwind config) so Django picks up the styles without extra steps.
- Postgres and Redis are exposed via Docker networks; the Django settings load their hostnames from `.env`.
