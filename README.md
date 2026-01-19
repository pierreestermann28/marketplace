# Swipe2Sell — Dockerized development

1 upload → IA → DetectedItem → swipe → listing, with Django + Celery + Redis + Tailwind in Docker.

## Quick start

1. Copy the env template:
   ```bash
   cp .env.example .env
   ```
2. Build & start the full stack (web, Celery worker, Tailwind watcher, Postgres, Redis, Flower):
   ```bash
   docker compose up --build
   ```
   The shared entrypoint waits for Postgres and Redis, runs `python manage.py migrate --noinput`, then hands control over to each service's command. Because we bind-mount the project into `/app`, Django, Celery, and Tailwind watch the source files for hot reload behavior.

## Services overview

- **web** – runs `python manage.py runserver 0.0.0.0:8000` for automatic Python code reload, so edits to views/templates are reflected immediately. Logs are streamed by `docker compose logs -f web`.
- **worker** – Celery worker (`--pool=solo`) processes ingestion and notification tasks; it shares the same bind mount so code changes lift without rebuilding.
- **tailwind** – executes `npm run tailwind:watch`, compiling Tailwind layers into `static/css/app.css` and keeping an eye on `theme/`/`tailwind.config.js`. The watch output prints through `docker compose logs tailwind`.
- **flower** – Celery monitoring at http://localhost:5555/ (port-forwarded from the container); starts with the same codebase plus `SKIP_MIGRATE=1`.
- **postgres**/ **redis** – standard containers with health checks; the web/worker services resolve them via `POSTGRES_HOST=postgres` and `REDIS_HOST=redis`.

## Handy commands

- Run migrations manually again if you touched model files:
  ```bash
  docker compose exec web python manage.py migrate
  ```
- Create a superuser or run other Django CLI commands:
  ```bash
  docker compose exec web python manage.py createsuperuser
  docker compose exec web python manage.py shell
  ```
- Peek at Tailwind output or restart the watcher:
  ```bash
  docker compose logs -f tailwind
  docker compose restart tailwind
  ```
- Watch Celery via Flower:
  ```bash
  open http://localhost:5555/
  docker compose logs -f flower
  ```

## Tips for smooth dev

- Hot reload works because `.` is mounted into `/app` for every service; editing Python, templates, or CSS/JS files triggers Django/Tailwind restarts automatically.
- Tailwind compiles into `static/css/app.css`, which Django loads from `STATICFILES_DIRS`, so no extra asset build step is needed.
- Use `docker compose exec web manage.py collectstatic --noinput` before deploying if you ever bundle static assets.
- If you skip migrations (e.g., on worker or Flower), set `SKIP_MIGRATE=1` in `.env`.
