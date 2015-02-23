from django.contrib import admin
from reversion import VersionAdmin
from mwsauth.models import MWSUser


class MWSUserAdmin(VersionAdmin):
    list_display = ('uid', 'ssh_public_key', 'user')
    search_fields = ('user', 'uid')


admin.site.register(MWSUser, MWSUserAdmin)
