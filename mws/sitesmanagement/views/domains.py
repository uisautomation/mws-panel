"""Views(Controllers) for managing Domain Names"""

from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render, redirect
from apimws.ansible import launch_ansible
from apimws.utils import ip_register_api_request
from mwsauth.utils import privileges_check
from sitesmanagement.models import Vhost, DomainNameFormNew, DomainName
from sitesmanagement.utils import is_camacuk


@login_required
def domains_management(request, vhost_id):
    """View(Controller) to show the list of domains names associated a the selected vhost. The template/view associated
     allows the user to add or delete domain names and to select a domain name as the main domain name for the vhost"""
    vhost = get_object_or_404(Vhost, pk=vhost_id)
    site = privileges_check(vhost.service.site.id, request.user)
    service = vhost.service

    if site is None:
        return HttpResponseForbidden()

    if not service or not service.active or service.is_busy:
        return HttpResponseRedirect(reverse('sitesmanagement.views.show', kwargs={'site_id': site.id}))

    breadcrumbs = {
        0: dict(name='Manage Web Service server: ' + str(site.name), url=reverse('sitesmanagement.views.show',
                                                                                 kwargs={'site_id': site.id})),
        1: dict(name='Server settings' if vhost.service.primary else 'Test server settings',
                url=reverse('sitesmanagement.views.service_settings', kwargs={'service_id': vhost.service.id})),
        2: dict(name='Web sites management: %s' % vhost.name, url=reverse('sitesmanagement.views.vhosts_management',
                                                                          kwargs={'service_id': vhost.service.id})),
        3: dict(name='Domain Names management', url=reverse(domains_management, kwargs={'vhost_id': vhost.id}))
    }

    return render(request, 'mws/domains.html', {
        'breadcrumbs': breadcrumbs,
        'vhost': vhost,
        'site': site,
        'service': vhost.service,
        'domain_form': DomainNameFormNew()
    })


@login_required
def add_domain(request, vhost_id, socket_error=None):
    """View(Controller) to add a domain name to the vhost selected. """
    vhost = get_object_or_404(Vhost, pk=vhost_id)
    site = privileges_check(vhost.service.site.id, request.user)
    service = vhost.service

    if site is None:
        return HttpResponseForbidden()

    if not service or not service.active or service.is_busy:
        return HttpResponseRedirect(reverse('sitesmanagement.views.show', kwargs={'site_id': site.id}))

    if request.method == 'POST':
        domain_form = DomainNameFormNew(request.POST)
        if domain_form.is_valid():
            domain_requested = domain_form.save(commit=False)
            if domain_requested.name != '':  # TODO do it after saving a domain request
                if is_camacuk(domain_requested.name):
                    new_domain = DomainName.objects.create(name=domain_requested.name, status='requested', vhost=vhost)
                    ip_register_api_request.delay(new_domain)
                else:
                    new_domain = DomainName.objects.create(name=domain_requested.name, status='accepted', vhost=vhost)
                    if vhost.main_domain is None:
                        vhost.main_domain = new_domain
                        vhost.save()
                launch_ansible(vhost.service)  # to add the new domain name to the vhost apache configuration
        else:
            breadcrumbs = {
                0: dict(name='Manage Web Service server: ' + str(site.name), url=reverse('sitesmanagement.views.show',
                                                                                         kwargs={'site_id': site.id})),
                1: dict(name='Server settings' if vhost.service.primary else 'Test server settings',
                        url=reverse('sitesmanagement.views.service_settings',
                                    kwargs={'service_id': vhost.service.id})),
                2: dict(name='Web sites management: %s' % vhost.name,
                        url=reverse('sitesmanagement.views.vhosts_management',
                                    kwargs={'service_id': vhost.service.id})),
                3: dict(name='Domain Names management', url=reverse(domains_management, kwargs={'vhost_id': vhost.id}))
            }

            return render(request, 'mws/domains.html', {
                'breadcrumbs': breadcrumbs,
                'vhost': vhost,
                'site': site,
                'service': vhost.service,
                'domain_form': domain_form,
                'error': True
            })

    return redirect(reverse('sitesmanagement.views.domains_management', kwargs={'vhost_id': vhost.id}))


@login_required
def set_dn_as_main(request, domain_id):
    """View(Controller) to set the domain name selected as the main domain of the vhost"""
    domain = get_object_or_404(DomainName, pk=domain_id)
    vhost = domain.vhost
    site = privileges_check(vhost.service.site.id, request.user)
    service = vhost.service

    if site is None:
        return HttpResponseForbidden()

    if not service or not service.active or service.is_busy:
        return HttpResponseRedirect(reverse('sitesmanagement.views.show', kwargs={'site_id': site.id}))

    if request.method == 'POST':
        vhost.main_domain = domain
        vhost.save()
        launch_ansible(vhost.service)  # to update the vhost main domain name in the apache configuration

    return HttpResponseRedirect(reverse('sitesmanagement.views.domains_management', kwargs={'vhost_id': vhost.id}))


@login_required
def delete_dn(request, domain_id):
    """View(Controller) to delete the domain name selected."""
    domain = get_object_or_404(DomainName, pk=domain_id)
    vhost = domain.vhost
    site = privileges_check(vhost.service.site.id, request.user)
    service = vhost.service

    if site is None:
        return HttpResponseForbidden()

    if not service or not service.active or service.is_busy:
        return HttpResponseRedirect(reverse('sitesmanagement.views.show', kwargs={'site_id': site.id}))

    if request.method == 'DELETE':
        if is_camacuk(domain.name):
            domain.status = 'to_be_deleted'
            domain.save()
        else:
            domain.delete()
        launch_ansible(vhost.service)
        return HttpResponseRedirect(reverse('sitesmanagement.views.domains_management', kwargs={'vhost_id': vhost.id}))

    return HttpResponseForbidden()
