import pathlib

from django.core.management import BaseCommand, call_command


class Command(BaseCommand):
    help = "Load every fixture file inside the fixtures/ folder (alphabetical order)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            default="fixtures",
            help="Directory where fixture files live (defaults to fixtures/).",
        )
        parser.add_argument(
            "--pattern",
            default="*.json",
            help="Glob pattern for fixture files.",
        )

    def handle(self, *args, **options):
        root = pathlib.Path(options["path"])
        if not root.exists():
            self.stdout.write(self.style.ERROR(f"{root} does not exist."))
            return
        fixtures = sorted(root.glob(options["pattern"]))
        if not fixtures:
            self.stdout.write(self.style.WARNING("No fixture files found."))
            return
        for fixture in fixtures:
            self.stdout.write(f"Loading {fixture.name}...")
            call_command("loaddata", str(fixture))
