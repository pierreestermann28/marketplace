import csv
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify

from location.models import City


def _coerce_decimal(value):
    try:
        return Decimal(value)
    except (InvalidOperation, TypeError, ValueError):
        return None


def _normalize_code(value, length=2):
    code = (value or "").strip()
    if code.isdigit():
        return code.zfill(length)
    return code


class Command(BaseCommand):
    help = "Import French city catalog into the location.City table."

    def add_arguments(self, parser):
        default_path = (
            settings.BASE_DIR
            / "static"
            / "cities"
            / "20230823-communes-departement-region.csv"
        )
        parser.add_argument(
            "--path",
            type=Path,
            default=default_path,
            help="Source CSV describing communes (default: %(default)s).",
        )

    def handle(self, *args, **options):
        csv_path: Path = options["path"]
        if not csv_path.exists():
            raise CommandError(f"City import file not found at {csv_path}")

        cities = []
        seen = set()

        with csv_path.open(encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                name = (
                    row.get("nom_commune_complet")
                    or row.get("nom_commune")
                    or row.get("nom_commune_postal")
                    or ""
                ).strip()
                postal_code = (row.get("code_postal") or "").strip()
                if not name or not postal_code:
                    continue

                postal_code = (
                    postal_code.zfill(5) if postal_code.isdigit() else postal_code
                )
                key = (name.lower(), postal_code)
                if key in seen:
                    continue
                seen.add(key)

                slug = slugify(f"{name}-{postal_code}")
                if not slug:
                    slug = f"city-{postal_code}"
                department_code = _normalize_code(row.get("code_departement"))
                region_code = _normalize_code(row.get("code_region"))

                city = City(
                    name=name,
                    postal_code=postal_code,
                    slug=slug,
                    department_code=department_code,
                    department_name=(row.get("nom_departement") or "").strip(),
                    region_code=region_code,
                    region_name=(row.get("nom_region") or "").strip(),
                    latitude=_coerce_decimal(row.get("latitude")),
                    longitude=_coerce_decimal(row.get("longitude")),
                )
                cities.append(city)

        if not cities:
            self.stdout.write(
                self.style.WARNING("No cities were imported (check the source file).")
            )
            return

        City.objects.all().delete()
        City.objects.bulk_create(cities, batch_size=1000)
        self.stdout.write(
            self.style.SUCCESS(f"Imported {len(cities):,} cities into location.City.")
        )
