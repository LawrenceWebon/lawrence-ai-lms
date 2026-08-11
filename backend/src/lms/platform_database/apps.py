from django.apps import AppConfig


class PlatformDatabaseConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "lms.platform_database"
    label = "platform_database"
