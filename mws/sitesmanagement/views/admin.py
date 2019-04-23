from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import render
from ucamlookup import validate_crsid_list

from sitesmanagement.models import Site


@login_required
def admin_search(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden()

    parameters = {}

    if request.method == 'POST':
        if 'mwsname' in request.POST and request.POST['mwsname']:
            sites = Site.objects.filter(name__contains=request.POST['mwsname'], preallocated=False)
            parameters['results'] = sites
        elif 'mwshostname' in request.POST and request.POST['mwshostname']:
            sites = Site.objects.filter(services__virtual_machines__network_configuration__name__contains=
                                        request.POST['mwshostname'], preallocated=False)
            parameters['results'] = sites
        elif 'mwsdomainname' in request.POST and request.POST['mwsdomainname']:
            sites = Site.objects.filter(services__vhosts__domain_names__name__contains=request.POST['mwsdomainname'],
                                        preallocated=False)
            parameters['results'] = sites
        elif 'crsid' in request.POST and request.POST['crsid']:
            user = validate_crsid_list(request.POST.getlist('crsid'))[0]
            sites = filter(lambda site: user in site.list_of_all_type_of_users(),
                           Site.objects.filter(preallocated=False))
            parameters['results'] = sites

    return render(request, 'mws/admin/search.html', parameters)
