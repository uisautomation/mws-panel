from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls import patterns, include, url
from django.contrib import admin

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'mws.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    url(r'^grappelli/', include('grappelli.urls')),
    url(r'', include('pyroven.urls')),
    url(r'^admin/', include(admin.site.urls)),

    # SitesManagement app
    url(r'^$', 'SitesManagement.views.index'),
    url(r'^show/(?P<site_id>[0-9]+)/$', 'SitesManagement.views.show'),
    url(r'^billing/(?P<site_id>[0-9]+)/$', 'SitesManagement.views.billing'),
    url(r'^new/$', 'SitesManagement.views.new'),
    url(r'^privacy/$', 'SitesManagement.views.privacy'),

    # apimws app
    url(r'^api/confirm_vm/(?P<vm_id>[0-9]+)/$', 'apimws.views.confirm_vm'),
    url(r'^api/findPeople$', 'apimws.views.find_people'),
    url(r'^api/findGroups$', 'apimws.views.find_groups'),

    # mwsauth app
    url(r'^mws/(?P<site_id>[0-9]+)/auth/$', 'mwsauth.views.auth_change'),


) + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
