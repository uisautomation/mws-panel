from django.contrib import admin
from reversion import VersionAdmin
from apimws.models import AnsibleConfiguration, ApacheModule, PHPLib


class AnsibleConfigurationAdmin(VersionAdmin):

    model = AnsibleConfiguration
    list_display = ('key', 'value', 'service')


admin.site.register(AnsibleConfiguration, AnsibleConfigurationAdmin)
admin.site.register(ApacheModule, VersionAdmin)
admin.site.register(PHPLib, VersionAdmin)
