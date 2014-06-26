from django.conf.urls import patterns, include, url
from campl_jquery_ui import views

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'campl.views.home', name='home'),
    # url(r'^campl/', include('campl.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # url(r'^admin/', include(admin.site.urls)),
    
    # if you use campl_context_preprocessors.py to add tabs, the url should look like this:
    # (r'^address/$', views.campl_view, {'active_tab_name':'A valid name'}),
    (r'^example/$', views.example, {'active_tab_name':'Main'}),
)
