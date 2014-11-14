from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, HttpResponseForbidden
from django.shortcuts import render, redirect
from ucamlookup import validate_crsids
from apimws.utils import launch_ansible_site
from mwsauth.models import MWSUser
from mwsauth.utils import privileges_check
from sitesmanagement.views import show, index
from mwsauth.validators import validate_groupids


@login_required
def auth_change(request, site_id):
    site = privileges_check(site_id, request.user)

    if site is None:
        return HttpResponseForbidden()

    lookup_lists = {
        'authorised_users': site.users.all(),
        'sshuserlist': site.ssh_users.all(),
        'authorised_groups': site.groups.all(),
        'sshusers_groups': site.ssh_groups.all()
    }

    if request.method == 'POST':
        authuserlist = validate_crsids(request.POST.get('users_crsids'))
        sshuserlist = validate_crsids(request.POST.get('sshusers_crsids'))
        authgrouplist = validate_groupids(request.POST.get('groupids'))
        sshauthgrouplist = validate_groupids(request.POST.get('sshgroupids'))
        # TODO If there are no users in the list return an Exception? No users authorised but maybe a group currently a
        # ValidationError is raised in validate_groupids
        site.users.clear()
        site.users.add(*authuserlist)
        site.ssh_users.clear()
        site.ssh_users.add(*sshuserlist)
        site.groups.clear()
        site.groups.add(*authgrouplist)
        site.ssh_groups.clear()
        site.ssh_groups.add(*sshauthgrouplist)
        launch_ansible_site(site)  # to add or delete users from the ssh/login auth list of the server
        return HttpResponseRedirect(reverse('sitesmanagement.views.show', kwargs={'site_id': site.id}))

    breadcrumbs = {
        0: dict(name='Manage Web Server: ' + str(site.name), url=reverse(show, kwargs={'site_id': site.id})),
        1: dict(name='Authorisation', url=reverse(auth_change, kwargs={'site_id': site.id}))
    }

    return render(request, 'mws/auth.html', {
        'lookup_lists': lookup_lists,
        'breadcrumbs': breadcrumbs,
        'site': site
    })


@login_required
def user_panel(request):
    breadcrumbs = {
        0: dict(name='User panel', url=reverse(user_panel))
    }

    if request.method == 'POST':
        if hasattr(request.user, 'mws_user'):
            mws_user = request.user.mws_user
            mws_user.ssh_public_key = 123
            mws_user.save()
        else:
            mws_user = MWSUser.objects.create(user=request.user, ssh_public_key=123)
        return redirect(index)

    return render(request, 'user/panel.html', {
        'breadcrumbs': breadcrumbs,
        'ssh_public_key': request.user.mws_user.ssh_public_key if hasattr(request.user, 'mws_user') else None
    })
