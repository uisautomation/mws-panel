from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls import patterns, include, url
from django.contrib import admin
from SitesManagement import views

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'MWS.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    url(r'^grappelli/', include('grappelli.urls')),
    url(r'', include('pyroven.urls')),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^$', views.index),
    url(r'^show/(?P<site_id>[0-9]+)/$', views.show),
    url(r'^billing/(?P<site_id>[0-9]+)/$', views.billing),
    url(r'^new/$', views.new),
    url(r'^privacy/$', views.privacy),
) + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
