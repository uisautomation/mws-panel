from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls import patterns, include, url
from django.contrib import admin

admin.autodiscover() # TODO not needed in django 1.7

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
    url(r'^show/(?P<site_id>[0-9]+)/$', 'sitesmanagement.views.show'),
    url(r'^settings/(?P<site_id>[0-9]+)/$', 'sitesmanagement.views.settings'),
    url(r'^billing/(?P<site_id>[0-9]+)/$', 'sitesmanagement.views.billing_management'),
    url(r'^new/$', 'sitesmanagement.views.new'),
    url(r'^edit/(?P<site_id>[0-9]+)/$', 'sitesmanagement.views.edit'),
    url(r'^privacy/$', 'sitesmanagement.views.privacy'),
    url(r'^domains/(?P<vhost_id>[0-9]+)/$', 'sitesmanagement.views.domains_management'),
    url(r'^vhosts/(?P<site_id>[0-9]+)/$', 'sitesmanagement.views.vhosts_management'),
    url(r'^add_domain/(?P<vhost_id>[0-9]+)/$', 'sitesmanagement.views.add_domain'),
    url(r'^add_vhost/(?P<site_id>[0-9]+)/$', 'sitesmanagement.views.add_vhost'),
    url(r'^set_dn_as_main/(?P<domain_id>[0-9]+)/$', 'sitesmanagement.views.set_dn_as_main'),
    url(r'^system_packages/(?P<site_id>[0-9]+)/$', 'sitesmanagement.views.system_packages'),
    url(r'^settings/vm/(?P<vm_id>[0-9]+)/on/$', 'sitesmanagement.views.power_vm'),
    url(r'^settings/vm/(?P<vm_id>[0-9]+)/reset/$', 'sitesmanagement.views.reset_vm'),

    # apimws app
    url(r'^api/confirm_vm/(?P<vm_id>[0-9]+)/$', 'apimws.views.confirm_vm'),
    url(r'^api/confirm_dns/(?P<dn_id>[0-9]+)/$', 'apimws.views.confirm_dns'),
    url(r'^api/finance/billing/(?P<year>20[0-9]{2})/$', 'apimws.views.billing_year'),
    url(r'^confirm_email/(?P<ec_id>[0-9]+)/(?P<token>(\w|\-)+)/$', 'apimws.views.confirm_email'),
    url(r'^api/dns/(?P<token>(\w|\-)+)/entries.json$', 'apimws.views.dns_entries'),

    # settings site
    url(r'^settings/vm/(?P<vm_id>[0-9]+)/status/$', 'sitesmanagement.views.check_vm_status'),

    # mwsauth app
    url(r'^auth/(?P<site_id>[0-9]+)/$', 'mwsauth.views.auth_change'),


) + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
