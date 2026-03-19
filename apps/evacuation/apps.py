from django.apps import AppConfig


class EvacuationConfig(AppConfig):
    """
    Django app configuration for evacuation module.

    Manages container evacuation records from terminals to port.
    Tracks daily/nightly shifts with SD-level container lists.
    """
    name = 'apps.evacuation'
