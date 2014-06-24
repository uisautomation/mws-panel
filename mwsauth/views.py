from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, HttpResponseForbidden
from django.shortcuts import render, get_object_or_404, redirect
from SitesManagement.models import Site
from SitesManagement.views import show
from mwsauth.validators import validate_crsids, validate_groupids


@login_required
def auth_change(request, site_id):
    site = get_object_or_404(Site, pk=site_id)

    if not site in request.user.sites.all():
        return HttpResponseForbidden()

    if site.is_admin_suspended():
        return redirect(reverse('SitesManagement.views.show', kwargs={'site_id': site.id}))

    authorised_users = site.users.all()
    authorised_groups = site.groups.all()

    if request.method == 'POST':
        authuserlist = validate_crsids(request.POST.get('crsids'))
        authgrouplist = validate_groupids(request.POST.get('groupids'))
        site.users.clear()
        site.users.add(*authuserlist)
        site.groups.clear()
        site.groups.add(*authgrouplist)
        return HttpResponseRedirect(reverse('SitesManagement.views.show', kwargs={'site_id': site.id}))

    breadcrumbs = {}
    breadcrumbs[0] = dict(name='Manage Web Server: '+str(site.name), url=reverse(show, kwargs={'site_id': site.id}))
    breadcrumbs[1] = dict(name='Authorisation', url=reverse(auth_change, kwargs={'site_id': site.id}))

    return render(request, 'mws/auth.html', {
        'authorised_users': authorised_users,
        'authorised_groups': authorised_groups,
        'breadcrumbs': breadcrumbs,
        'site': site
    })