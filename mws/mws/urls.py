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

    # sitesmanagement app
    url(r'^$', 'sitesmanagement.views.index'),
    url(r'^show/(?P<site_id>[0-9]+)/$', 'sitesmanagement.views.show'),
    url(r'^billing/(?P<site_id>[0-9]+)/$', 'sitesmanagement.views.billing'),
    url(r'^new/$', 'sitesmanagement.views.new'),
    url(r'^edit/(?P<site_id>[0-9]+)/$', 'sitesmanagement.views.edit'),
    url(r'^privacy/$', 'sitesmanagement.views.privacy'),
    url(r'^domains/(?P<site_id>[0-9]+)/$', 'sitesmanagement.views.domains_management'),
    url(r'^set_dn_as_main/(?P<site_id>[0-9]+)/(?P<domain_id>[0-9]+)/$', 'sitesmanagement.views.set_dn_as_main'),

    # apimws app
    url(r'^api/confirm_vm/(?P<vm_id>[0-9]+)/$', 'apimws.views.confirm_vm'),
    url(r'^api/confirm_dns/(?P<dn_id>[0-9]+)/$', 'apimws.views.confirm_dns'),
    url(r'^api/findPeople$', 'apimws.views.find_people'),
    url(r'^api/findGroups$', 'apimws.views.find_groups'),
    url(r'^api/finance/billing/(?P<year>20[0-9]{2})/$', 'apimws.views.billing_year'),

    # mwsauth app
    url(r'^mws/(?P<site_id>[0-9]+)/auth/$', 'mwsauth.views.auth_change'),


) + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
