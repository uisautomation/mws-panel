from django.contrib import admin
from django.contrib.admin import ModelAdmin
from reversion import VersionAdmin
from .models import Site, Billing, DomainName, ServiceNetworkConfig, Suspension, VirtualMachine, EmailConfirmation, \
    Vhost, UnixGroup, HostNetworkConfig, SiteKeys
from ucamlookup import get_institutions, get_institution_name_by_id


class SiteAdmin(ModelAdmin):
    all_institutions = get_institutions()

    list_display = ('name', 'description', 'institution', 'primary_vm', 'secondary_vm', 'disabled', 'canceled')
    ordering = ('name', )
    search_fields = ('name', )
    list_filter = ('institution_id', 'disabled', )

    def institution(self, obj):
        return get_institution_name_by_id(obj.institution_id, self.all_institutions)

    def primary_vm_name(self, obj):
        if obj.primary_vm:
            return obj.primary_vm
        else:
            return None

    def secondary_vm_name(self, obj):
        if obj.secondary_vm:
            return obj.secondary_vm
        else:
            return None

    def canceled(self, obj):
        return obj.is_canceled()

    institution.admin_order_field = 'institution_id'


class DomainNameAdmin(VersionAdmin):
    list_display = ('name', 'vhost', 'status')
    ordering = ('name', )
    search_fields = ('name', )
    list_filter = ('vhost', 'status')


class SuspensionAdmin(ModelAdmin):
    list_display = ('site', 'start_date', 'end_date', 'active')
    list_filter = ('site__name', 'active')


class NetworkConfigAdmin(ModelAdmin):
    list_display = ('IPv4', 'IPv6', 'mws_domain', 'site', 'IPv4private', 'mws_private_domain')
    # list_filter = ('used', )

    def used(self, obj):
        if obj.site:
            return True
        else:
            return False

    def public(self, obj):
        return obj.is_public()

    public.boolean = True


class BillingAdmin(VersionAdmin):
    list_display = ('site', 'group', )


class VhostAdmin(VersionAdmin):
    list_display = ('name', 'vm', )


class VirtualMachineAdmin(VersionAdmin):
    list_display = ('name', 'site', 'primary', 'status')


class EmailConfirmationAdmin(ModelAdmin):
    list_display = ('email', 'site', 'status')


admin.site.register(Site, SiteAdmin)
admin.site.register(Billing, BillingAdmin)
admin.site.register(Vhost, VhostAdmin)
admin.site.register(DomainName, DomainNameAdmin)
admin.site.register(ServiceNetworkConfig, NetworkConfigAdmin)
admin.site.register(Suspension, SuspensionAdmin)
admin.site.register(VirtualMachine, VirtualMachineAdmin)
admin.site.register(EmailConfirmation, EmailConfirmationAdmin)
admin.site.register(UnixGroup, VersionAdmin)
admin.site.register(HostNetworkConfig, VersionAdmin)
admin.site.register(SiteKeys, VersionAdmin)
