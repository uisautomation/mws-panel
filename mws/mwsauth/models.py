from django.contrib.auth.models import User
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.db import models


class MWSUser(models.Model):
    ssh_public_key = models.TextField(null=True, blank=True)
    uid = models.IntegerField()
    user = models.OneToOneField(User, to_field='username', related_name='mws_user', db_constraint=False)


@receiver(pre_save, sender=User)
def add_name_to_user(instance, **kwargs):
    if len(MWSUser.objects.filter(user=instance.username)) == 0:
        instance.is_active = False


def get_mws_public_key(self):
    if hasattr(self, 'mws_user'):
        return self.mws_user.ssh_public_key
    else:
        return None


User.get_mws_public_key = get_mws_public_key
