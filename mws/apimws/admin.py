from django.contrib import admin
from django.contrib.admin import ModelAdmin
from reversion import VersionAdmin
from apimws.models import AnsibleConfiguration


class AnsibleConfigurationAdmin(VersionAdmin):

    model = AnsibleConfiguration
    list_display = ('key', 'value', 'vm')


admin.site.register(AnsibleConfiguration, AnsibleConfigurationAdmin)
