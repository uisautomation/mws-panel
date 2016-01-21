from django.contrib import admin
from django.contrib.admin import ModelAdmin
from django.contrib.admin.utils import model_ngettext
from django.core.checks import messages
from django.contrib.admin import helpers
from django.template.response import TemplateResponse
from django.utils.encoding import force_text
from reversion import VersionAdmin
from .models import Site, Billing, DomainName, Suspension, VirtualMachine, EmailConfirmation, \
    Vhost, UnixGroup, NetworkConfig, SiteKey, Service, Snapshot
from ucamlookup import get_institutions, get_institution_name_by_id, IbisException


def recreate_vm(modeladmin, request, queryset):
    opts = modeladmin.model._meta

    # The user has already confirmed the deletion.
    # Do the deletion and return a None to display the change list view again.
    if request.POST.get('post'):
        n = queryset.count()
        if n:
            for vm in queryset:
                from apimws.vm import destroy_vm, recreate_vm
                try:
                    destroy_vm(vm.id)
                except:
                    pass
                recreate_vm(vm.id)

            modeladmin.message_user(request, "Successfully recreated %(count)d %(items)s." % {
                "count": n, "items": model_ngettext(modeladmin.opts, n)
            }, messages.INFO)
        # Return None to display the change list page again.
        return None

    if len(queryset) == 1:
        objects_name = force_text(opts.verbose_name)
    else:
        objects_name = force_text(opts.verbose_name_plural)

    context = dict(
        # modeladmin.admin_site.each_context(request), TODO Only Django 1.8
        modeladmin.admin_site.each_context(),
        title="Are you sure?",
        objects_name=objects_name,
        list_objects=[queryset],
        queryset=queryset,
        opts=opts,
        action_checkbox_name=helpers.ACTION_CHECKBOX_NAME,
        media=modeladmin.media,
    )

    request.current_app = modeladmin.admin_site.name

    # Display the confirmation page
    return TemplateResponse(request, "admin/recreate_confirmation.html", context)


recreate_vm.short_description = "Recreate VM"


def execute_ansible(modeladmin, request, queryset):
    from apimws.ansible import launch_ansible
    for service in queryset:
        launch_ansible(service)


execute_ansible.short_description = "Launch Ansible"


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
        return get_institution_name_by_id(obj.institution_id, self.all_institutions) if obj.institution_id else ''

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

    actions = [execute_ansible]


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


class VirtualMachineAdmin(VersionAdmin):
    # form = VirtualMachineForm
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
