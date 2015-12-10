from django.contrib import admin
from django.contrib.admin import ModelAdmin
from django.forms import ModelForm
from reversion import VersionAdmin
from suit.widgets import LinkedSelect
from .models import Site, Billing, DomainName, Suspension, VirtualMachine, EmailConfirmation, \
    Vhost, UnixGroup, NetworkConfig, SiteKey, Service, Snapshot
from ucamlookup import get_institutions, get_institution_name_by_id, IbisException


def recreate_vm(modeladmin, request, queryset):
    from apimws.vm import destroy_vm, recreate_vm
    for vm in queryset:
        try:
            destroy_vm(vm.id)
        except:
            pass
        recreate_vm(vm.id)


recreate_vm.short_description = "Recreate VM"


def get_institutions_no_exception():
    try:
        get_institutions()
    except IbisException:
        return []


class SiteAdmin(ModelAdmin):
    all_institutions = get_institutions_no_exception()

    list_display = ('name', 'institution', 'primary_vm', 'secondary_vm', 'start_date', 'disabled', 'canceled')
    ordering = ('name', 'start_date')
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
    canceled.boolean = True

    institution.admin_order_field = 'institution_id'


class ServiceAdmin(VersionAdmin):
    list_display = ('site', 'type', 'fqdn', 'status')
    ordering = ('site', 'type')
    search_fields = ('name', 'site')

    def fqdn(self, obj):
        return str(obj)


class SiteKeyAdmin(VersionAdmin):
    list_display = ('type', 'site')
    ordering = ('site', 'type')
    search_fields = ('site__name', )


class DomainNameAdmin(VersionAdmin):
    list_display = ('name', 'vhost', 'get_site', 'status')
    ordering = ('name', )
    search_fields = ('name', )
    list_filter = ('vhost', 'status')

    def get_site(self, obj):
        return obj.vhost.service.site
    get_site.short_description = 'Site'
    get_site.admin_order_field = 'vhost__service__site'


class SuspensionAdmin(ModelAdmin):
    list_display = ('site', 'start_date', 'end_date', 'active')
    list_filter = ('site__name', 'active')


class NetworkConfigAdmin(ModelAdmin):
    list_display = ('IPv4', 'IPv6', 'name', 'service')
    # list_filter = ('used', )

    def used(self, obj):
        if obj.service:
            return True
        else:
            return False

    def public(self, obj):
        return obj.is_public()

    public.boolean = True


class BillingAdmin(VersionAdmin):
    list_display = ('site', 'group', 'date_created', 'date_modified', 'date_sent_to_finance')


class VhostAdmin(VersionAdmin):
    list_display = ('name', 'service', )


class SnapshotAdmin(ModelAdmin):
    list_display = ('name', 'date', 'service', )


class VirtualMachineForm(ModelForm):
    class Meta:
        widgets = {
            'service': LinkedSelect
        }


class VirtualMachineAdmin(VersionAdmin):
    form = VirtualMachineForm
    list_display = ('name', 'site', 'services')

    def services(self, obj):
        return '<a href="/admin/sitesmanagement/service/%d/">%s</a>' % (obj.service.id, obj.service)

    services.allow_tags = True

    actions = [recreate_vm]


class EmailConfirmationAdmin(ModelAdmin):
    list_display = ('email', 'site', 'status')


admin.site.register(Site, SiteAdmin)
admin.site.register(Billing, BillingAdmin)
admin.site.register(Vhost, VhostAdmin)
admin.site.register(DomainName, DomainNameAdmin)
admin.site.register(Suspension, SuspensionAdmin)
admin.site.register(VirtualMachine, VirtualMachineAdmin)
admin.site.register(EmailConfirmation, EmailConfirmationAdmin)
admin.site.register(UnixGroup, VersionAdmin)
admin.site.register(NetworkConfig, NetworkConfigAdmin)
admin.site.register(Service, ServiceAdmin)
admin.site.register(SiteKey, SiteKeyAdmin)
admin.site.register(Snapshot, SnapshotAdmin)
