from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls import patterns, include, url
from django.contrib import admin

urlpatterns = patterns('',
    # external apps urls
    url(r'^grappelli/', include('grappelli.urls')),
    url(r'', include('ucamwebauth.urls')),

    # admin app urls
    url(r'^admin/', include(admin.site.urls)),

    # lookup/ibis urls
    url(r'^ucamlookup/', include('ucamlookup.urls')),

    # sitesmanagement app
    url(r'^$', 'sitesmanagement.views.index'),
    url(r'^new/$', 'sitesmanagement.views.new'),
    url(r'^show/(?P<site_id>[0-9]+)/$', 'sitesmanagement.views.show'),
    url(r'^edit/(?P<site_id>[0-9]+)/$', 'sitesmanagement.views.edit'),
    url(r'^settings/(?P<vm_id>[0-9]+)/$', 'sitesmanagement.views.settings'),
    url(r'^billing/(?P<site_id>[0-9]+)/$', 'sitesmanagement.views.billing_management'),
    url(r'^delete/(?P<site_id>[0-9]+)/$', 'sitesmanagement.views.delete'),
    url(r'^disable/(?P<site_id>[0-9]+)/$', 'sitesmanagement.views.disable'),
    url(r'^enable/(?P<site_id>[0-9]+)/$', 'sitesmanagement.views.enable'),
    url(r'^privacy/$', 'sitesmanagement.views.privacy'),
    url(r'^domains/(?P<vhost_id>[0-9]+)/$', 'sitesmanagement.views.domains_management'),
    url(r'^vhosts/(?P<vm_id>[0-9]+)/$', 'sitesmanagement.views.vhosts_management'),
    url(r'^vhosts/(?P<vhost_id>[0-9]+)/delete/$', 'sitesmanagement.views.delete_vhost'),
    url(r'^vhosts/(?P<vhost_id>[0-9]+)/certificates/$', 'sitesmanagement.views.certificates'),
    url(r'^vhosts/(?P<vhost_id>[0-9]+)/generate_csr/$', 'sitesmanagement.views.generate_csr'),
    url(r'^visit_website/(?P<vhost_id>[0-9]+)/$', 'sitesmanagement.views.visit_vhost'),
    url(r'^add_domain/(?P<vhost_id>[0-9]+)/$', 'sitesmanagement.views.add_domain'),
    url(r'^delete_domain/(?P<domain_id>[0-9]+)/$', 'sitesmanagement.views.delete_dn'),
    url(r'^add_vhost/(?P<vm_id>[0-9]+)/$', 'sitesmanagement.views.add_vhost'),
    url(r'^set_dn_as_main/(?P<domain_id>[0-9]+)/$', 'sitesmanagement.views.set_dn_as_main'),
    url(r'^system_packages/(?P<vm_id>[0-9]+)/$', 'sitesmanagement.views.system_packages'),
    url(r'^clone_vm/(?P<site_id>[0-9]+)/$', 'sitesmanagement.views.clone_vm_view'),
    url(r'^delete_vm/(?P<vm_id>[0-9]+)/$', 'sitesmanagement.views.delete_vm'),
    url(r'^settings/vm/(?P<vm_id>[0-9]+)/on/$', 'sitesmanagement.views.power_vm'),
    url(r'^settings/vm/(?P<vm_id>[0-9]+)/reset/$', 'sitesmanagement.views.reset_vm'),
    url(r'^unix_groups/(?P<vm_id>[0-9]+)/$', 'sitesmanagement.views.unix_groups'),
    url(r'^unix_groups/(?P<vm_id>[0-9]+)/add/$', 'sitesmanagement.views.add_unix_group'),
    url(r'^unix_groups/edit/(?P<ug_id>[0-9]+)/$', 'sitesmanagement.views.unix_group'),
    url(r'^unix_groups/delete/(?P<ug_id>[0-9]+)/$', 'sitesmanagement.views.delete_unix_group'),
    url(r'^settings/vm/(?P<vm_id>[0-9]+)/db_root_pass/$', 'sitesmanagement.views.change_db_root_password'),

    # apimws app
    url(r'^api/confirm_dns/(?P<dn_id>[0-9]+)/$', 'apimws.views.confirm_dns'),
    url(r'^api/finance/billing/(?P<year>20[0-9]{2})/$', 'apimws.views.billing_year'),
    url(r'^confirm_email/(?P<ec_id>[0-9]+)/(?P<token>(\w|\-)+)/$', 'apimws.views.confirm_email'),
    url(r'^api/dns/(?P<token>(\w|\-)+)/entries.json$', 'apimws.views.dns_entries'),

    # settings site
    url(r'^settings/vm/(?P<vm_id>[0-9]+)/status/$', 'sitesmanagement.views.check_vm_status'),

    # mwsauth app
    url(r'^auth/(?P<site_id>[0-9]+)/$', 'mwsauth.views.auth_change'),

    # user panel
    url(r'^user_panel/$', 'mwsauth.views.user_panel'),

) + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
