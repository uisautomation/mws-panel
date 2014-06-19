from django.contrib import admin
from django.contrib.admin import ModelAdmin
from SitesManagement.models import Site, Billing, DomainName, NetworkConfig, Suspension, VirtualMachine


admin.site.register(Site, ModelAdmin)
admin.site.register(Billing, ModelAdmin)
admin.site.register(DomainName, ModelAdmin)
admin.site.register(NetworkConfig, ModelAdmin)
admin.site.register(Suspension, ModelAdmin)
admin.site.register(VirtualMachine, ModelAdmin)