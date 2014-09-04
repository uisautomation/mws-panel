import datetime
import socket
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, HttpResponseForbidden, JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from ucamlookup import get_group_ids_of_a_user_in_lookup, IbisException, user_in_groups
from apimws.models import AnsibleConfiguration
from apimws.platforms import PlatformsAPINotWorkingException
from apimws.utils import email_confirmation, platforms_email_api_request, ip_register_api_request, launch_ansible
from mwsauth.utils import get_or_create_group_by_groupid, privileges_check
from sitesmanagement.utils import is_camacuk, get_object_or_None
from .models import SiteForm, DomainNameFormNew, BillingForm, DomainName, NetworkConfig, EmailConfirmation, \
    VirtualMachine, SystemPackagesForm, Vhost, VhostForm, Site


@login_required
def index(request):
    try:
        groups_id = get_group_ids_of_a_user_in_lookup(request.user)
    except IbisException as e:
        groups_id = []

    sites = []
    for group_id in groups_id:
        group = get_or_create_group_by_groupid(group_id)
        sites += group.sites.all()

    sites += request.user.sites.all()

    return render(request, 'index.html', {
        'all_sites': sorted(set(sites)),
        'deactivate_new': NetworkConfig.num_pre_allocated() < 1
    })


@login_required
def new(request):
    if NetworkConfig.num_pre_allocated() < 1:
        return HttpResponseRedirect(reverse('sitesmanagement.views.index'))

    breadcrumbs = {
        0: dict(name='New Manage Web Server', url=reverse(new))
    }

    # TODO: FIX: if SiteForm's name field is empty then DomainNameForm errors are also shown
    if request.method == 'POST':
        site_form = SiteForm(request.POST, prefix="siteform", user=request.user)
        if site_form.is_valid():

            site = site_form.save(commit=False)
            site.start_date = datetime.date.today()
            site.save()

            # Save user that requested the site
            site.users.add(request.user)

            try:
                platforms_email_api_request(site, primary=True)  # TODO do it after saving a site
            except Exception as e:
                raise e  # TODO try again later. pass to celery?

            try:
                if site.email:
                    email_confirmation(site)  # TODO do it after saving a site
            except Exception as e:
                raise e  # TODO try again later. pass to celery?

            return HttpResponseRedirect(reverse('sitesmanagement.views.show', kwargs={'site_id': site.id}))
    else:
        site_form = SiteForm(prefix="siteform", user=request.user)

    return render(request, 'mws/new.html', {
        'site_form': site_form,
        'breadcrumbs': breadcrumbs
    })


@login_required
def edit(request, site_id):
    site = privileges_check(site_id, request.user)

    if site is None:
        return HttpResponseForbidden()

    if site.primary_vm is not None and site.primary_vm.is_ready is False:
        return HttpResponseRedirect(reverse('sitesmanagement.views.show', kwargs={'site_id': site.id}))

    breadcrumbs = {
        0: dict(name='Manage Web Server: ' + str(site.name), url=reverse(show, kwargs={'site_id': site.id})),
        1: dict(name='Change information about your MWS',
                           url=reverse('sitesmanagement.views.edit', kwargs={'site_id': site.id}))
    }

    if request.method == 'POST':
        site_form = SiteForm(request.POST, user=request.user, instance=site)
        if site_form.is_valid():
            site_form.save()
            if 'email' in site_form.changed_data:
                try:
                    if site.email:
                        email_confirmation(site)  # TODO do it in other place?
                except Exception as e:
                    raise e  # TODO try again later. pass to celery?
            return HttpResponseRedirect(reverse('sitesmanagement.views.show', kwargs={'site_id': site.id}))
    else:
        site_form = SiteForm(user=request.user, instance=site)

    return render(request, 'mws/edit.html', {
        'site_form': site_form,
        'site': site,
        'breadcrumbs': breadcrumbs
    })


@login_required
def show(request, site_id):
    site = get_object_or_404(Site, pk=site_id)

    try:
        if (not site in request.user.sites.all() and not user_in_groups(request.user, site.groups.all())) \
                or site.is_admin_suspended():
            return HttpResponseForbidden()
    except Exception as e:
        return HttpResponseForbidden()

    breadcrumbs = {
        0: dict(name='Manage Web Server: ' + str(site.name), url=reverse(show, kwargs={'site_id': site.id}))
    }

    warning_messages = []

    if site.primary_vm is not None and site.primary_vm.status == 'ansible':
        warning_messages.append("Your virtual machine is being configured.")

    for vhost in site.vhosts.all():
        for domain_name in vhost.domain_names.all():
            if domain_name.status == 'requested':
                warning_messages.append("Your domain name %s has been requested and is under review." %
                                        domain_name.name)

    if not hasattr(site, 'billing'):
        warning_messages.append("No Billing, please add one.")

    if site.email:
        site_email = EmailConfirmation.objects.get(email=site.email, site_id=site.id)
        if site_email.status == 'pending':
            warning_messages.append("Your email '%s' is still unconfirmed, please click on the link of the sent email"
                                    % site.email)

    if site.primary_vm is None or site.primary_vm.status == 'requested':
        warning_messages.append("Your Manage Web Server is being prepared")

    return render(request, 'mws/show.html', {
        'breadcrumbs': breadcrumbs,
        'warning_messages': warning_messages,
        'site': site
    })


@login_required
def billing_management(request, site_id):
    site = privileges_check(site_id, request.user)

    if site is None:
        return HttpResponseForbidden()

    if site.primary_vm is not None and site.primary_vm.is_ready is False:
        return HttpResponseRedirect(reverse('sitesmanagement.views.show', kwargs={'site_id': site.id}))

    breadcrumbs = {
        0: dict(name='Manage Web Server: ' + str(site.name), url=reverse(show, kwargs={'site_id': site.id})),
        1: dict(name='Billing', url=reverse(billing_management, kwargs={'site_id': site.id}))
    }

    if request.method == 'POST':
        if hasattr(site, 'billing'):
            billing_form = BillingForm(request.POST, request.FILES, instance=site.billing)
            if billing_form.is_valid():
                billing_form.save()
                return HttpResponseRedirect(reverse('sitesmanagement.views.show', kwargs={'site_id': site.id}))
        else:
            billing_form = BillingForm(request.POST, request.FILES)
            if billing_form.is_valid():
                billing = billing_form.save(commit=False)
                billing.site = site
                billing.save()
                return HttpResponseRedirect(reverse('sitesmanagement.views.show', kwargs={'site_id': site.id}))
    elif hasattr(site, 'billing'):
        billing_form = BillingForm(instance=site.billing)
    else:
        billing_form = BillingForm()

    return render(request, 'mws/billing.html', {
        'breadcrumbs': breadcrumbs,
        'site': site,
        'billing_form': billing_form
    })


def privacy(request):
    return render(request, 'index.html', {})


@login_required
def vhosts_management(request, site_id):
    site = privileges_check(site_id, request.user)

    if site is None:
        return HttpResponseForbidden()

    if site.primary_vm is not None and site.primary_vm.is_ready is False:
        return HttpResponseRedirect(reverse('sitesmanagement.views.show', kwargs={'site_id': site.id}))

    breadcrumbs = {
        0: dict(name='Manage Web Server: ' + str(site.name), url=reverse(show, kwargs={'site_id': site.id})),
        1: dict(name='Vhosts Management', url=reverse(vhosts_management, kwargs={'site_id': site.id}))
    }

    return render(request, 'mws/vhosts.html', {
        'breadcrumbs': breadcrumbs,
        'site': site
    })


@login_required
def add_vhost(request, site_id):
    site = privileges_check(site_id, request.user)

    if site is None:
        return HttpResponseForbidden()

    if site.primary_vm is not None and site.primary_vm.is_ready is False:
        return HttpResponseRedirect(reverse('sitesmanagement.views.show', kwargs={'site_id': site.id}))

    breadcrumbs = {
        0: dict(name='Manage Web Server: ' + str(site.name), url=reverse(show, kwargs={'site_id': site.id})),
        1: dict(name='Vhosts Management', url=reverse(vhosts_management, kwargs={'site_id': site.id})),
        2: dict(name='Add Vhost', url=reverse(add_vhost, kwargs={'site_id': site.id}))
    }

    if request.method == 'POST':
        vhost_form = VhostForm(request.POST)
        if vhost_form.is_valid():
            vhost = vhost_form.save(commit=False)
            vhost.site = site
            vhost.save()
            launch_ansible(site)  # to create a new vhost configuration file
            return HttpResponseRedirect(reverse('sitesmanagement.views.vhosts_management',
                                                kwargs={'site_id': site.id}))
    else:
        vhost_form = VhostForm()

    return render(request, 'mws/add_vhost.html', {
        'breadcrumbs': breadcrumbs,
        'site': site,
        'vhost_form': vhost_form,
    })


@login_required
def delete_vhost(request, vhost_id):
    vhost = get_object_or_404(Vhost, pk=vhost_id)
    site = privileges_check(vhost.site.id, request.user)

    if site is None:
        return HttpResponseForbidden()

    if request.method == 'DELETE':
        vhost.delete()
        launch_ansible(site)
        return redirect(show, site_id=site.id)

    return HttpResponseForbidden()


@login_required
def domains_management(request, vhost_id):
    vhost = get_object_or_404(Vhost, pk=vhost_id)
    site = privileges_check(vhost.site.id, request.user)

    if site is None:
        return HttpResponseForbidden()

    if site.primary_vm is not None and site.primary_vm.is_ready is False:
        return HttpResponseRedirect(reverse('sitesmanagement.views.show', kwargs={'site_id': site.id}))

    breadcrumbs = {
        0: dict(name='Manage Web Server: ' + str(site.name), url=reverse(show, kwargs={'site_id': site.id})),
        1: dict(name='Vhosts Management', url=reverse(vhosts_management, kwargs={'site_id': site.id})),
        2: dict(name='Domains Management', url=reverse(domains_management, kwargs={'vhost_id': vhost.id}))
    }

    return render(request, 'mws/domains.html', {
        'breadcrumbs': breadcrumbs,
        'vhost': vhost
    })


@login_required
def set_dn_as_main(request, domain_id):  # TODO remove vhost_id
    domain = get_object_or_404(DomainName, pk=domain_id)
    vhost = domain.vhost
    site = privileges_check(vhost.site.id, request.user)

    if site is None:
        return HttpResponseForbidden()

    if site.primary_vm is not None and site.primary_vm.is_ready is False:
        return HttpResponseRedirect(reverse('sitesmanagement.views.show', kwargs={'site_id': site.id}))

    if domain not in vhost.domain_names.all():
        return HttpResponseForbidden()

    if request.method == 'POST':
        vhost.main_domain = domain
        vhost.save()
        launch_ansible(site)  # to update the vhost main domain name in the apache configuration

    return HttpResponseRedirect(reverse('sitesmanagement.views.domains_management', kwargs={'vhost_id': vhost.id}))


@login_required
def add_domain(request, vhost_id, socket_error=None):
    vhost = get_object_or_404(Vhost, pk=vhost_id)
    site = privileges_check(vhost.site.id, request.user)

    if site is None:
        return HttpResponseForbidden()

    if site.primary_vm is not None and site.primary_vm.is_ready is False:
        return HttpResponseRedirect(reverse('sitesmanagement.views.show', kwargs={'site_id': site.id}))

    breadcrumbs = {
        0: dict(name='Manage Web Server: ' + str(site.name), url=reverse(show, kwargs={'site_id': site.id})),
        1: dict(name='Vhosts Management', url=reverse(vhosts_management, kwargs={'site_id': site.id})),
        2: dict(name='Domains Management', url=reverse(domains_management, kwargs={'vhost_id': vhost.id})),
        3: dict(name='Add Domain', url=reverse(add_domain, kwargs={'vhost_id': vhost.id}))
    }

    if request.method == 'POST':
        domain_form = DomainNameFormNew(request.POST)
        if domain_form.is_valid():
            try:
                domain_requested = domain_form.save(commit=False)
                if domain_requested.name != '':  # TODO do it after saving a domain request
                    if is_camacuk(domain_requested.name):
                        ip_register_api_request(vhost, domain_requested.name)
                    else:
                        new_domain = DomainName.objects.create(name=domain_requested.name, status='accepted',
                                                               vhost=vhost)
                        if vhost.main_domain is None:
                            vhost.main_domain = new_domain
                            vhost.save()
                    launch_ansible(site)  # to add the new domain name to the vhost apache configuration
            except socket.error as serr:
                pass  # TODO sent an error to infosys email?
            except Exception as e:
                raise e  # TODO try again later. pass to celery?
            return HttpResponseRedirect(reverse('sitesmanagement.views.domains_management',
                                                kwargs={'vhost_id': vhost.id}))
    else:
        domain_form = DomainNameFormNew()

    return render(request, 'mws/add_domain.html', {
        'breadcrumbs': breadcrumbs,
        'vhost': vhost,
        'domain_form': domain_form,
    })


@login_required
def settings(request, site_id):
    site = privileges_check(site_id, request.user)

    if site is None:
        return HttpResponseForbidden()

    if site.primary_vm is not None and site.primary_vm.is_ready is False:
        return HttpResponseRedirect(reverse('sitesmanagement.views.show', kwargs={'site_id': site.id}))

    vm = site.primary_vm

    if vm is None or vm.status != 'ready':
        return redirect(reverse(show, kwargs={'site_id': site.id}))

    breadcrumbs = {
        0: dict(name='Manage Web Server: ' + str(site.name), url=reverse(show, kwargs={'site_id': site.id})),
        1: dict(name='Settings', url=reverse(settings, kwargs={'site_id': site.id}))
    }

    return render(request, 'mws/settings.html', {
        'breadcrumbs': breadcrumbs,
        'site': site,
        'primary_vm': vm,
    })


@login_required
def check_vm_status(request, vm_id):
    vm = get_object_or_404(VirtualMachine, pk=vm_id)
    site = privileges_check(vm.site.id, request.user)

    if site is None:
        return HttpResponseForbidden()

    if site.primary_vm is not None and site.primary_vm.is_ready is False:
        return HttpResponseRedirect(reverse('sitesmanagement.views.show', kwargs={'site_id': site.id}))

    if vm is None or vm.status != 'ready':
        return JsonResponse({'error': 'VMNotReady'})

    try:
        return JsonResponse({'vm_is_on': vm.is_on()})
    except PlatformsAPINotWorkingException:
        return JsonResponse({'error': 'PlatformsAPINotWorking'})


@login_required
def system_packages(request, site_id):
    site = privileges_check(site_id, request.user)

    if site is None:
        return HttpResponseForbidden()

    if site.primary_vm is not None and site.primary_vm.is_ready is False:
        return HttpResponseRedirect(reverse('sitesmanagement.views.show', kwargs={'site_id': site.id}))

    ansible_configuraton = get_object_or_None(AnsibleConfiguration, site=site, key="System Packages")

    breadcrumbs = {
        0: dict(name='Manage Web Server: ' + str(site.name), url=reverse(show, kwargs={'site_id': site.id})),
        1: dict(name='Settings', url=reverse(settings, kwargs={'site_id': site.id})),
        2: dict(name='System packages', url=reverse(system_packages, kwargs={'site_id': site.id}))
    }

    if request.method == 'POST':
        system_packages_form = SystemPackagesForm(request.POST)
        if system_packages_form.is_valid():
            if ansible_configuraton is not None:
                ansible_configuraton.value = ",".join(system_packages_form.cleaned_data.get('system_packages'))
                ansible_configuraton.save()
            else:
                AnsibleConfiguration.objects.create(site=site, key="System Packages",
                                                    value=",".join(
                                                        system_packages_form.cleaned_data.get('system_packages')))
            launch_ansible(site)  # to install or delete new/old packages selected by the user
            return HttpResponseRedirect(reverse('sitesmanagement.views.show',
                                                kwargs={'site_id': site.id}))
    else:
        if ansible_configuraton is not None:
            system_packages_form = SystemPackagesForm(initial={'system_packages':
                                                                   ansible_configuraton.value.split(",")})
        else:
            system_packages_form = SystemPackagesForm()

    return render(request, 'mws/system_packages.html', {
        'breadcrumbs': breadcrumbs,
        'site': site,
        'system_packages_form': system_packages_form,
    })


@login_required
def power_vm(request, vm_id):
    vm = get_object_or_404(VirtualMachine, pk=vm_id)
    site = privileges_check(vm.site.id, request.user)

    if site is None:
        return HttpResponseForbidden()

    if site.primary_vm is not None and site.primary_vm.is_ready is False:
        return HttpResponseRedirect(reverse('sitesmanagement.views.show', kwargs={'site_id': site.id}))

    if vm is None or vm.status != 'ready':
        return redirect(reverse(show, kwargs={'site_id': site.id}))

    vm.power_on()

    return redirect(settings, site_id=site.id)


@login_required
def reset_vm(request, vm_id):
    vm = get_object_or_404(VirtualMachine, pk=vm_id)
    site = privileges_check(vm.site.id, request.user)

    if site is None:
        return HttpResponseForbidden()

    if site.primary_vm is not None and site.primary_vm.is_ready is False:
        return HttpResponseRedirect(reverse('sitesmanagement.views.show', kwargs={'site_id': site.id}))

    if vm is None or vm.status != 'ready':
        return redirect(reverse(show, kwargs={'site_id': site.id}))

    if vm.do_reset() is False:
        pass  # TODO add error messages in session if it is False

    return redirect(settings, site_id=site.id)