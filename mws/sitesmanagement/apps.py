from django.apps import AppConfig
from django.conf import settings


class SitesManagementConfig(AppConfig):
    """
    Configuration for the sites management application.

    """
    name = "sitesmanagement"

    _DEFAULT_SETTINGS = {
        'MWS_DOMAIN_NAME_GRACE_DAYS': 10
    }

    def ready(self):
        """
        Perform application-specific initialisation.

        """
        # Register default settings in a rather ugly way since Django does not
        # have a cleaner way for apps to register default settings.
        # https://stackoverflow.com/questions/8428556/
        for name, value in self._DEFAULT_SETTINGS.items():
            if not hasattr(settings, name):
                setattr(settings, name, value)

        # import (and, hence, register) signal handlers. The import is done
        # within ready() to minimise disruption from importing application
        # code. See: https://docs.djangoproject.com/en/1.8/topics/signals/.
        from . import signals
