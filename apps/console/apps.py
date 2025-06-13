"""
Console app configuration for CommuMap Admin Console.

Initializes singleton managers and sets up the admin console functionality.
"""
from django.apps import AppConfig


class ConsoleConfig(AppConfig):
    """
    Configuration for the admin console app.
    
    Handles initialization of singleton managers and app setup.
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.console'
    verbose_name = 'Admin Console'
    
    def ready(self):
        """Initialize app components when Django starts."""
        try:
            # Import signal handlers if any
            # from . import signals
            
            # Note: Singleton managers will be initialized when first accessed
            # to avoid database access during app initialization
            pass
            
        except Exception as e:
            # Handle import errors during migrations or initial setup
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Could not initialize console app components: {e}")
