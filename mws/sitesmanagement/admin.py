from django.contrib import admin
from django.contrib.admin import ModelAdmin
from .models import Site, Billing, DomainName, NetworkConfig, Suspension, VirtualMachine, EmailConfirmation
from .utils import get_institutions, get_institution_name_by_id


class SiteAdmin(ModelAdmin):

    all_institutions = get_institutions()

    model = Site
    list_display = ('name', 'description', 'institution', 'primary_vm' )
    ordering = ('name', )
    search_fields = ('name', )
    list_filter = ('institution_id', )

    def institution(self, obj):
        return get_institution_name_by_id(obj.institution_id, self.all_institutions)

    def primary_vm_name(self, obj):
        if obj.primary_vm():
            return obj.primary_vm()
        else:
            return None

    institution.admin_order_field = 'institution_id'


class DomainNameAdmin(ModelAdmin):

    model = Site
    list_display = ('name', 'site', 'status' )
    ordering = ('name', )
    search_fields = ('name', )
    list_filter = ('site', 'status')


class SuspensionAdmin(ModelAdmin):

    model = Suspension
    list_display = ('site', 'start_date', 'end_date', 'active')
    list_filter = ('site__name', 'active')


class NetworkConfigAdmin(ModelAdmin):

    model = NetworkConfig
    list_display = ('IPv4', 'IPv6', 'mws_domain', 'virtual_machine')
    #list_filter = ('used', )

    def used(self, obj):
        if obj.virtual_machine:
            return True
        else:
            return False


class BillingAdmin(ModelAdmin):

    model = Billing
    list_display = ('site', 'group', )


class VirtualMachineAdmin(ModelAdmin):

    model = VirtualMachine
    list_display = ('name', 'site', 'primary', 'status', 'network_configuration')


class EmailConfirmationAdmin(ModelAdmin):

    model = EmailConfirmation
    list_display = ('email', 'site', 'status')


admin.site.register(Site, SiteAdmin)
admin.site.register(Billing, BillingAdmin)
admin.site.register(DomainName, DomainNameAdmin)
admin.site.register(NetworkConfig, NetworkConfigAdmin)
admin.site.register(Suspension, SuspensionAdmin)
admin.site.register(VirtualMachine, VirtualMachineAdmin)
admin.site.register(EmailConfirmation, EmailConfirmationAdmin)