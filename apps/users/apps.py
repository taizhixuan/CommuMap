from django.apps import AppConfig


class UsersConfig(AppConfig):
    """
    Django app configuration for the users application.
    
    This app handles user profiles, preferences, bookmarks, and user-specific
    functionality within the CommuMap platform.
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.users'
    verbose_name = 'Users'
    
    def ready(self) -> None:
        """
        Perform initialization tasks when the app is ready.
        
        This method is called once Django has loaded all models and is ready
        to handle requests. Used to register signal handlers and perform
        other initialization tasks.
        """
        try:
            import apps.users.signals  # noqa F401
        except ImportError:
            pass 