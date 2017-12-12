from django.contrib import admin
from django.contrib.admin import ModelAdmin
from reversion.admin import VersionAdmin
from apimws.models import AnsibleConfiguration, PHPLib, Host, Cluster


class AnsibleConfigurationAdmin(VersionAdmin):

    model = AnsibleConfiguration
    list_display = ('key', 'value', 'service')


admin.site.register(AnsibleConfiguration, AnsibleConfigurationAdmin)
# admin.site.register(ApacheModule, VersionAdmin)
admin.site.register(PHPLib, VersionAdmin)
admin.site.register(Cluster, ModelAdmin)
admin.site.register(Host, ModelAdmin)
