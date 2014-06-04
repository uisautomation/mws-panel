from django.template import RequestContext
from django.shortcuts import render_to_response

def example(request, active_tab_name):
    breadcrumbs = {}
    # This is just a demo.
    # See campl-page-header.html for more information about how to use breadcrumbs.
    breadcrumbs[0] = dict(name="Breadcrumb", url='http://www.cam.ac.uk/')
    return render_to_response('campl.html', {'breadcrumbs':breadcrumbs, 'active_tab_name':active_tab_name},context_instance=RequestContext(request))