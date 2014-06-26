from django.contrib import admin
from django.contrib.admin import ModelAdmin
from .models import Site, Billing, DomainName, NetworkConfig, Suspension, VirtualMachine
from .utils import get_institutions, get_institution_name_by_id


class SiteAdmin(ModelAdmin):

    all_institutions = get_institutions()

    model = Site
    list_display = ('name', 'description', 'institution' )
    ordering = ('name', )
    search_fields = ('name', )
    list_filter = ('institution_id', )

    def institution(self, obj):
        return get_institution_name_by_id(obj.institution_id, self.all_institutions)

    institution.admin_order_field = 'institution_id'


class DomainNameAdmin(ModelAdmin):

    model = Site
    list_display = ('name', 'site', 'status' )
    ordering = ('name', )
    search_fields = ('name', )
    list_filter = ('site', 'status')


admin.site.register(Site, SiteAdmin)
admin.site.register(Billing, ModelAdmin)
admin.site.register(DomainName, DomainNameAdmin)
admin.site.register(NetworkConfig, ModelAdmin)
admin.site.register(Suspension, ModelAdmin)
admin.site.register(VirtualMachine, ModelAdmin)