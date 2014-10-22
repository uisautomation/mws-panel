from django.contrib import admin
from reversion import VersionAdmin
from mwsauth.models import MWSUser


class MWSUserAdmin(VersionAdmin):
    list_display = ('user', 'ssh_public_key', )


admin.site.register(MWSUser, MWSUserAdmin)