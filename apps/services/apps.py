"""
Services app configuration for CommuMap.
"""
from django.apps import AppConfig


class ServicesConfig(AppConfig):
    """Configuration for the services app."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.services'
    verbose_name = 'Services'
    
    def ready(self) -> None:
        """Import signals when the app is ready."""
        import apps.services.signals  # noqa 