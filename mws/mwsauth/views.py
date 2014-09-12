from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, HttpResponseForbidden
from django.shortcuts import render, get_object_or_404, redirect
from apimws.utils import launch_ansible
from sitesmanagement.models import Site
from sitesmanagement.views import show
from mwsauth.validators import validate_crsids, validate_groupids
from ucamlookup import user_in_groups


@login_required
def auth_change(request, site_id):
    site = get_object_or_404(Site, pk=site_id)

    if site.is_canceled():
        return HttpResponseForbidden()

    # If the user is not in the user auth list of the site and neither belongs to a group in the group auth list of
    # the site then return a forbidden response
    if not site in request.user.sites.all() and not user_in_groups(request.user, site.groups.all()):
        return HttpResponseForbidden()

    if site.is_admin_suspended():
        return redirect(reverse('sitesmanagement.views.show', kwargs={'site_id': site.id}))

    authorised_users = site.users.all()
    authorised_groups = site.groups.all()

    if request.method == 'POST':
        authuserlist = validate_crsids(request.POST.get('crsids'))
        authgrouplist = validate_groupids(request.POST.get('groupids'))
        # TODO If there are no users in the list return an Exception? No users authorised but maybe a group currently a
        # ValidationError is raised in validate_groupids
        site.users.clear()
        site.users.add(*authuserlist)
        site.groups.clear()
        site.groups.add(*authgrouplist)
        launch_ansible(site)  # to add or delete users from the ssh/login auth list of the server
        return HttpResponseRedirect(reverse('sitesmanagement.views.show', kwargs={'site_id': site.id}))

    breadcrumbs = {
        0: dict(name='Manage Web Server: ' + str(site.name), url=reverse(show, kwargs={'site_id': site.id})),
        1: dict(name='Authorisation', url=reverse(auth_change, kwargs={'site_id': site.id}))
    }

    return render(request, 'mws/auth.html', {
        'lookup_users_list': authorised_users,
        'lookup_group_list': authorised_groups,
        'breadcrumbs': breadcrumbs,
        'site': site
    })