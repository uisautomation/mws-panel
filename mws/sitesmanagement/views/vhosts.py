"""Views(Controllers) for managing Vhosts"""

from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render, redirect
from apimws.ansible import launch_ansible
from mwsauth.utils import privileges_check
from sitesmanagement.models import Service, VhostForm, Vhost


@login_required
def vhosts_management(request, service_id):
    """View(Controller) to show the current list of vhosts for a service. For each vhost you can go to manage
    tls key/certificates, and domain names for this vhost, or add a new vhost"""
    service = get_object_or_404(Service, pk=service_id)
    site = privileges_check(service.site.id, request.user)

    if site is None:
        return HttpResponseForbidden()

    if not service or not service.active or service.is_busy:
        return HttpResponseRedirect(reverse('sitesmanagement.views.show', kwargs={'site_id': site.id}))

    breadcrumbs = {
        0: dict(name='Manage Web Service server: ' + str(site.name), url=reverse('sitesmanagement.views.show',
                                                                                 kwargs={'site_id': site.id})),
        1: dict(name='Server settings' if service.primary else 'Test server settings',
                url=reverse('sitesmanagement.views.service_settings', kwargs={'service_id': service.id})),
        2: dict(name='Web sites management', url=reverse(vhosts_management, kwargs={'service_id': service.id}))
    }

    return render(request, 'mws/vhosts.html', {
        'breadcrumbs': breadcrumbs,
        'service': service,
        'site': site,
        'vhost_form': VhostForm()
    })


@login_required
def add_vhost(request, service_id):
    """View(Controller) to add a new vhost to the service. It shows a form with the Vhost required fields."""
    service = get_object_or_404(Service, pk=service_id)
    site = privileges_check(service.site.id, request.user)

    if site is None:
        return HttpResponseForbidden()

    if not service or not service.active or service.is_busy:
        return HttpResponseRedirect(reverse('sitesmanagement.views.show', kwargs={'site_id': site.id}))

    if request.method == 'POST':
        vhost_form = VhostForm(request.POST)
        if vhost_form.is_valid():
            vhost = vhost_form.save(commit=False)
            vhost.service = service
            vhost.save()
            launch_ansible(service)  # to create a new vhost configuration file

    return redirect(reverse('sitesmanagement.views.vhosts_management', kwargs={'service_id': service.id}))


@login_required
def visit_vhost(request, vhost_id):
    """View(Controller) to redirect the user to the URL of the vhost selected."""
    vhost = get_object_or_404(Vhost, pk=vhost_id)
    site = privileges_check(vhost.service.site.id, request.user)
    service = vhost.service

    if site is None:
        return HttpResponseForbidden()

    if not service or not service.active or service.is_busy:
        return HttpResponseRedirect(reverse('sitesmanagement.views.show', kwargs={'site_id': site.id}))

    return redirect("http://"+str(vhost.main_domain.name))


@login_required
def delete_vhost(request, vhost_id):
    """View(Controller) to delete the vhost selected."""
    vhost = get_object_or_404(Vhost, pk=vhost_id)
    site = privileges_check(vhost.service.site.id, request.user)
    service = vhost.service

    if site is None:
        return HttpResponseForbidden()

    if not service or not service.active or service.is_busy:
        return HttpResponseRedirect(reverse('sitesmanagement.views.show', kwargs={'site_id': site.id}))

    if request.method == 'DELETE':
        vhost.delete()
        launch_ansible(vhost.service)
        return redirect('sitesmanagement.views.show', site_id=site.id)

    return HttpResponseForbidden()
