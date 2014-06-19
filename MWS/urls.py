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
    url(r'^privacy/$', views.privacy),
)
