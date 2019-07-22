from django.contrib import admin
from django.contrib.auth.models import User
from reversion.admin import VersionAdmin

from .models import MWSUser


class UserAdmin(VersionAdmin):
    list_display = ('username', 'last_name', 'uid', 'is_staff', 'is_superuser')
    list_filter = ('is_staff', 'is_superuser')
    search_fields = ('username', )

    def uid(self, obj):
        if obj.mws_user:
            return obj.mws_user.uid
    uid.admin_order_field = 'mws_user__uid'

@admin.register(MWSUser)
class MWSUserAdmin(admin.ModelAdmin):
    pass

admin.site.unregister(User)
admin.site.register(User, UserAdmin)
