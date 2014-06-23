from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver
from apimws.utils import return_visibleName_by_crsid


@receiver(pre_save, sender=User)
def add_name_to_user(instance, **kwargs):
    user = instance
    if user is not None:
        user.last_name = return_visibleName_by_crsid(user.username)
        user.set_unusable_password()