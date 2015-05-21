"""Views(Controllers) for managing Unix Groups"""
from django.conf import settings

from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render, redirect
from ucamlookup import validate_crsids
from apimws.ansible import launch_ansible
from mwsauth.utils import privileges_check
from sitesmanagement.models import Service, UnixGroupForm, UnixGroup


@login_required
def unix_groups(request, service_id):
    if getattr(settings, 'DEMO', False):
        return HttpResponseRedirect(reverse('sitesmanagement.views.index'))
    service = get_object_or_404(Service, pk=service_id)
    site = privileges_check(service.site.id, request.user)

    if site is None:
        return HttpResponseForbidden()

    if not service or not service.active or service.is_busy:
        return redirect(site)

    breadcrumbs = {
        0: dict(name='Manage Web Service server: ' + str(site.name), url=site.get_absolute_url()),
        1: dict(name='Server settings' if service.primary else 'Test server settings',
                url=reverse('sitesmanagement.views.service_settings', kwargs={'service_id': service.id})),
        2: dict(name='Manage Unix Groups', url=reverse(unix_groups, kwargs={'service_id': service.id}))
    }

    return render(request, 'mws/unix_groups.html', {
        'breadcrumbs': breadcrumbs,
        'site': site,
        'service': service
    })


@login_required
def add_unix_group(request, service_id):
    if getattr(settings, 'DEMO', False):
        return HttpResponseRedirect(reverse('sitesmanagement.views.index'))
    service = get_object_or_404(Service, pk=service_id)
    site = privileges_check(service.site.id, request.user)

    if site is None:
        return HttpResponseForbidden()

    if not service or not service.active or service.is_busy:
        return redirect(site)

    breadcrumbs = {
        0: dict(name='Manage Web Service server: ' + str(site.name), url=site.get_absolute_url()),
        1: dict(name='Server settings' if service.primary else 'Test server settings',
                url=reverse('sitesmanagement.views.service_settings', kwargs={'service_id': service.id})),
        2: dict(name='Manage Unix Groups', url=reverse(unix_groups, kwargs={'service_id': service.id})),
        3: dict(name='Add a new Unix Group', url=reverse(add_unix_group, kwargs={'service_id': service.id}))
    }

    lookup_lists = {
        'unix_users': []  # TODO to be removed once django-ucam-lookup is modified
    }

    if request.method == 'POST':
        unix_group_form = UnixGroupForm(request.POST)
        if unix_group_form.is_valid():

            unix_group = unix_group_form.save(commit=False)
            unix_group.service = service
            unix_group.save()

            unix_users = validate_crsids(request.POST.get('unix_users'))
            # TODO If there are no users in the list return an Exception?
            unix_group.users.add(*unix_users)

            launch_ansible(service)  # to apply these changes to the vm
            return HttpResponseRedirect(reverse(unix_groups, kwargs={'service_id': service.id}))
    else:
        unix_group_form = UnixGroupForm()

    return render(request, 'mws/add_unix_group.html', {
        'breadcrumbs': breadcrumbs,
        'site': site,
        'service': service,
        'lookup_lists': lookup_lists,  # TODO to be removed once django-ucam-lookup is modified
        'unix_group_form': unix_group_form
    })


@login_required
def unix_group(request, ug_id):
    if getattr(settings, 'DEMO', False):
        return HttpResponseRedirect(reverse('sitesmanagement.views.index'))
    unix_group_i = get_object_or_404(UnixGroup, pk=ug_id)
    site = privileges_check(unix_group_i.service.site.id, request.user)
    service = unix_group_i.service

    if site is None:
        return HttpResponseForbidden()

    if not service or not service.active or service.is_busy:
        return redirect(site)

    breadcrumbs = {
        0: dict(name='Manage Web Service server: ' + str(site.name), url=site.get_absolute_url()),
        1: dict(name='Server settings' if unix_group_i.service.primary else 'Test server settings',
                url=reverse('sitesmanagement.views.service_settings', kwargs={'service_id': unix_group_i.service.id})),
        2: dict(name='Manage Unix Groups', url=reverse(unix_groups, kwargs={'service_id': unix_group_i.service.id})),
        3: dict(name='Edit Unix Group', url=reverse('sitesmanagement.views.unix_group',
                                                    kwargs={'ug_id': unix_group_i.id}))
    }

    lookup_lists = {
        'unix_users': unix_group_i.users.all()
    }

    if request.method == 'POST':
        unix_group_form = UnixGroupForm(request.POST, instance=unix_group_i)
        if unix_group_form.is_valid():
            unix_group_form.save()

            unix_users = validate_crsids(request.POST.get('unix_users'))
            # TODO If there are no users in the list return an Exception?
            unix_group_i.users.clear()
            unix_group_i.users.add(*unix_users)

            launch_ansible(unix_group_i.service)  # to apply these changes to the service
            return HttpResponseRedirect(reverse(unix_groups, kwargs={'service_id': unix_group_i.service.id}))
    else:
        unix_group_form = UnixGroupForm(instance=unix_group_i)

    return render(request, 'mws/unix_group.html', {
        'breadcrumbs': breadcrumbs,
        'lookup_lists': lookup_lists,
        'site': site,
        'service': unix_group_i.service,
        'unix_group_form': unix_group_form
    })


@login_required
def delete_unix_group(request, ug_id):
    if getattr(settings, 'DEMO', False):
        return HttpResponseRedirect(reverse('sitesmanagement.views.index'))
    unix_group = get_object_or_404(UnixGroup, pk=ug_id)
    site = privileges_check(unix_group.service.site.id, request.user)
    service = unix_group.service

    if site is None:
        return HttpResponseForbidden()

    if not service or not service.active or service.is_busy:
        return redirect(site)

    if request.method == 'DELETE':
        unix_group.delete()
        launch_ansible(unix_group.service)
        return redirect(unix_groups, service_id=unix_group.service.id)

    return HttpResponseForbidden()