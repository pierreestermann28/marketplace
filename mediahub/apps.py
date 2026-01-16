from django.apps import AppConfig


class MediaHubConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "mediahub"

    def ready(self):
        # Register signal handlers.
        from . import signals  # noqa: F401
