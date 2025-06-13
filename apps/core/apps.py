"""
Core app configuration for CommuMap.
"""
from django.apps import AppConfig


class CoreConfig(AppConfig):
    """Configuration for the core app."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.core'
    verbose_name = 'Core'
    
    def ready(self) -> None:
        """Import signals when the app is ready."""
        # import apps.core.signals  # noqa - Commented out until signals.py is created
        pass 