from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.core.management import BaseCommand, call_command
from django.db import connection


class Command(BaseCommand):
    help = "Drop/Postgres schema, rerun migrations, and load fixtures."

    def handle(self, *args, **options):
        engine = settings.DATABASES["default"]["ENGINE"]
        if "sqlite" in engine:
            db_path = settings.BASE_DIR / "db.sqlite3"
            if db_path.exists():
                db_path.unlink()
                self.stdout.write(self.style.SUCCESS("Removed existing db.sqlite3"))
            else:
                self.stdout.write("No sqlite database found, skipping removal.")
        else:
            with connection.cursor() as cursor:
                cursor.execute("DROP SCHEMA public CASCADE;")
                cursor.execute("CREATE SCHEMA public;")
            self.stdout.write(self.style.SUCCESS("Reset PostgreSQL schema"))

        self.ensure_migrations_packages()
        call_command("makemigrations")
        call_command("migrate")
        call_command("loaddatafixtures")

    def ensure_migrations_packages(self):
        base_dir = Path(settings.BASE_DIR).resolve()
        for app_config in apps.get_app_configs():
            app_path = Path(app_config.path).resolve()
            if not str(app_path).startswith(str(base_dir)):
                continue
            migrations_dir = app_path / "migrations"
            if not migrations_dir.exists():
                migrations_dir.mkdir()
            init_file = migrations_dir / "__init__.py"
            if not init_file.exists():
                init_file.write_text("", encoding="utf-8")
