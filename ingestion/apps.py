from django.apps import AppConfig


class IngestionConfig(AppConfig):
    name = "ingestion"

    def ready(self):
        from . import signals  # noqa: F401
