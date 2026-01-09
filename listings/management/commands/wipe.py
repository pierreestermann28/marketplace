from pathlib import Path

from django.conf import settings
from django.core.management import BaseCommand, call_command


class Command(BaseCommand):
    help = "Delete the sqlite database, rerun migrations, and load fixtures."

    def handle(self, *args, **options):
        db_path = settings.BASE_DIR / "db.sqlite3"
        if db_path.exists():
            db_path.unlink()
            self.stdout.write(self.style.SUCCESS("Removed existing db.sqlite3"))
        else:
            self.stdout.write("No sqlite database found, skipping removal.")

        call_command("makemigrations")
        call_command("migrate")
        call_command("loaddatafixtures")
