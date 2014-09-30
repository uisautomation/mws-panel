import datetime
import socket
import reversion
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.db import transaction
from django.http import HttpResponseRedirect, HttpResponseForbidden, JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from ucamlookup import get_group_ids_of_a_user_in_lookup, IbisException, user_in_groups
from apimws.models import AnsibleConfiguration
from apimws.platforms import PlatformsAPINotWorkingException, new_site_primary_vm, clone_vm
from apimws.utils import email_confirmation, ip_register_api_request, launch_ansible
from mwsauth.utils import get_or_create_group_by_groupid, privileges_check
from sitesmanagement.utils import is_camacuk, get_object_or_None
from .models import SiteForm, DomainNameFormNew, BillingForm, DomainName, NetworkConfig, EmailConfirmation, \
    VirtualMachine, SystemPackagesForm, Vhost, VhostForm, Site, UnixGroupForm, UnixGroup, SiteRequestDemo


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

    sites_enabled = filter(lambda site: not site.is_canceled() and not site.is_disabled(), sites)

    sites_disabled = filter(lambda site: not site.is_canceled() and site.is_disabled(), sites)

    return render(request, 'index.html', {
        'sites_enabled': sorted(set(sites_enabled)),
        'sites_disabled': sorted(set(sites_disabled)),
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

            SiteRequestDemo.objects.create(date_submitted=timezone.now(), site=site)

            try:
                new_site_primary_vm(site, primary=True)  # TODO do it after saving a site
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

    if site.is_busy:
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
                        # TODO launch ansible to update email associated
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
def delete(request, site_id):
    site = privileges_check(site_id, request.user)

    if site is None:
        return HttpResponseForbidden()

    if site.is_busy:
        return HttpResponseRedirect(reverse('sitesmanagement.views.show', kwargs={'site_id': site.id}))

    breadcrumbs = {
        0: dict(name='Manage Web Server: ' + str(site.name), url=reverse(show, kwargs={'site_id': site.id})),
        1: dict(name='Change information about your MWS',
                           url=reverse('sitesmanagement.views.edit', kwargs={'site_id': site.id})),
        2: dict(name='Delete your MWS', url=reverse('sitesmanagement.views.delete', kwargs={'site_id': site.id}))
    }

    if request.method == 'POST':
        if request.POST.get('confirmation') == "yes":
            site.cancel()
            return redirect(index)
        else:
            return redirect(reverse('sitesmanagement.views.show', kwargs={'site_id': site.id}))

    return render(request, 'mws/delete.html', {
        'site': site,
        'breadcrumbs': breadcrumbs
    })


@login_required
def disable(request, site_id):
    site = privileges_check(site_id, request.user)

    if site is None:
        return HttpResponseForbidden()

    if site.is_busy:
        return HttpResponseRedirect(reverse('sitesmanagement.views.show', kwargs={'site_id': site.id}))

    breadcrumbs = {
        0: dict(name='Manage Web Server: ' + str(site.name), url=reverse(show, kwargs={'site_id': site.id})),
        1: dict(name='Change information about your MWS',
                           url=reverse('sitesmanagement.views.edit', kwargs={'site_id': site.id})),
        2: dict(name='Disable your MWS site', url=reverse(clone_vm_view, kwargs={'site_id': site.id}))
    }

    if request.method == 'POST':
        if site.disable():
            return redirect(index)

    return render(request, 'mws/disable.html', {
        'breadcrumbs': breadcrumbs,
        'site': site,
    })


@login_required
def enable(request, site_id):
    site = get_object_or_404(Site, pk=site_id)

    try:
        if (not site in request.user.sites.all() and not user_in_groups(request.user, site.groups.all())) \
                or site.is_admin_suspended() or site.is_canceled():
            return HttpResponseForbidden()
    except Exception:
        return HttpResponseForbidden()

    if request.method == 'POST':
        if site.enable():
            return redirect(show, site_id=site.id)

    return redirect(index)


@login_required
def show(request, site_id):
    site = privileges_check(site_id, request.user)

    if site is None:
        return HttpResponseForbidden()

    breadcrumbs = {
        0: dict(name='Manage Web Server: ' + str(site.name), url=reverse(show, kwargs={'site_id': site.id}))
    }

    warning_messages = []

    if (timezone.now() - site.site_request_demo.date_submitted).seconds > 60:
        site.site_request_demo.demo_time_passed()

    if site.primary_vm is not None and site.primary_vm.status == 'ansible':
        warning_messages.append("Your primary virtual machine is being configured.")

    if site.secondary_vm is not None and site.secondary_vm.status == 'ansible':
        warning_messages.append("Your secondary virtual machine is being configured.")

    if site.primary_vm is not None:
        for vhost in site.primary_vm.vhosts.all():
            for domain_name in vhost.domain_names.all():
                if domain_name.status == 'requested':
                    warning_messages.append("Your domain name %s has been requested and is under review." %
                                            domain_name.name)

    if not hasattr(site, 'billing'):
        warning_messages.append("No Billing, please add one.")

    if site.email:
        site_email = EmailConfirmation.objects.get(email=site.email, site_id=site.id)
        if site_email.status == 'pending':
            warning_messages.append("Your email '%s' is still unconfirmed, please check your email inbox and click on "
                                    "the link of the email we sent you."
                                    % site.email)

    if site.primary_vm is None or site.primary_vm.status == 'requested':
        warning_messages.append("Your Managed Web Server is being prepared")

    return render(request, 'mws/show.html', {
        'breadcrumbs': breadcrumbs,
        'warning_messages': warning_messages,
        'site': site
    })


@login_required
@transaction.atomic()
@reversion.create_revision()
def billing_management(request, site_id):
    site = privileges_check(site_id, request.user)

    if site is None:
        return HttpResponseForbidden()

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


@login_required
def clone_vm_view(request, site_id):
    site = privileges_check(site_id, request.user)

    if site is None:
        return HttpResponseForbidden()

    if not site.is_ready:
        return HttpResponseRedirect(reverse('sitesmanagement.views.show', kwargs={'site_id': site.id}))

    breadcrumbs = {
        0: dict(name='Manage Web Server: ' + str(site.name), url=reverse(show, kwargs={'site_id': site.id})),
        1: dict(name='Clone your VM', url=reverse(clone_vm_view, kwargs={'site_id': site.id}))
    }

    if request.method == 'POST':
        if request.POST.get('primary_vm') == "true":
            if not clone_vm(site, True):
                raise PlatformsAPINotWorkingException()
        if request.POST.get('primary_vm') == "false":
            if not clone_vm(site, False):
                raise PlatformsAPINotWorkingException()

        return redirect(show, site_id = site.id)

    return render(request, 'mws/clone_vm.html', {
        'breadcrumbs': breadcrumbs,
        'site': site,
    })


def privacy(request):
    return render(request, 'index.html', {})


@login_required
def vhosts_management(request, vm_id):
    vm = get_object_or_404(VirtualMachine, pk=vm_id)
    site = privileges_check(vm.site.id, request.user)

    if site is None:
        return HttpResponseForbidden()

    if vm.is_busy:
        return HttpResponseRedirect(reverse('sitesmanagement.views.show', kwargs={'site_id': site.id}))

    breadcrumbs = {
        0: dict(name='Manage Web Server: ' + str(site.name), url=reverse(show, kwargs={'site_id': site.id})),
        1: dict(name='Settings', url=reverse(settings, kwargs={'vm_id': vm.id})),
        2: dict(name='Vhosts Management', url=reverse(vhosts_management, kwargs={'vm_id': vm.id}))
    }

    return render(request, 'mws/vhosts.html', {
        'breadcrumbs': breadcrumbs,
        'vm': vm
    })


@login_required
def add_vhost(request, vm_id):
    vm = get_object_or_404(VirtualMachine, pk=vm_id)
    site = privileges_check(vm.site.id, request.user)

    if site is None:
        return HttpResponseForbidden()

    if vm.is_busy:
        return HttpResponseRedirect(reverse('sitesmanagement.views.show', kwargs={'site_id': site.id}))

    breadcrumbs = {
        0: dict(name='Manage Web Server: ' + str(site.name), url=reverse(show, kwargs={'site_id': site.id})),
        1: dict(name='Settings', url=reverse(settings, kwargs={'vm_id': vm.id})),
        2: dict(name='Vhosts Management', url=reverse(vhosts_management, kwargs={'vm_id': vm.id})),
        3: dict(name='Add Vhost', url=reverse(add_vhost, kwargs={'vm_id': vm.id}))
    }

    if request.method == 'POST':
        vhost_form = VhostForm(request.POST)
        if vhost_form.is_valid():
            vhost = vhost_form.save(commit=False)
            vhost.vm = vm
            vhost.save()
            launch_ansible(site)  # to create a new vhost configuration file
            return HttpResponseRedirect(reverse('sitesmanagement.views.vhosts_management',
                                                kwargs={'vm_id': vm.id}))
    else:
        vhost_form = VhostForm()

    return render(request, 'mws/add_vhost.html', {
        'breadcrumbs': breadcrumbs,
        'vm': vm,
        'vhost_form': vhost_form,
    })


@login_required
def settings(request, vm_id):
    vm = get_object_or_404(VirtualMachine, pk=vm_id)
    site = privileges_check(vm.site.id, request.user)

    if site is None:
        return HttpResponseForbidden()

    if vm.is_busy:
        return HttpResponseRedirect(reverse('sitesmanagement.views.show', kwargs={'site_id': site.id}))

    if vm is None or vm.status != 'ready':
        return redirect(reverse(show, kwargs={'site_id': site.id}))

    breadcrumbs = {
        0: dict(name='Manage Web Server: ' + str(site.name), url=reverse(show, kwargs={'site_id': site.id})),
        1: dict(name='Settings', url=reverse(settings, kwargs={'vm_id': vm.id}))
    }

    return render(request, 'mws/settings.html', {
        'breadcrumbs': breadcrumbs,
        'site': site,
        'vm': vm,
    })


@login_required
def check_vm_status(request, vm_id):
    vm = get_object_or_404(VirtualMachine, pk=vm_id)
    site = privileges_check(vm.site.id, request.user)

    if site is None:
        return HttpResponseForbidden()

    if vm.is_busy:
        return HttpResponseRedirect(reverse('sitesmanagement.views.show', kwargs={'site_id': site.id}))

    if vm is None or vm.status != 'ready':
        return JsonResponse({'error': 'VMNotReady'})

    try:
        return JsonResponse({'vm_is_on': vm.is_on()})
    except PlatformsAPINotWorkingException:
        return JsonResponse({'error': 'PlatformsAPINotWorking'})


@login_required
def system_packages(request, vm_id):
    vm = get_object_or_404(VirtualMachine, pk=vm_id)
    site = privileges_check(vm.site.id, request.user)

    if site is None:
        return HttpResponseForbidden()

    if vm.is_busy:
        return HttpResponseRedirect(reverse('sitesmanagement.views.show', kwargs={'site_id': site.id}))

    ansible_configuraton = get_object_or_None(AnsibleConfiguration, vm=vm, key="System Packages")

    breadcrumbs = {
        0: dict(name='Manage Web Server: ' + str(site.name), url=reverse(show, kwargs={'site_id': site.id})),
        1: dict(name='Settings', url=reverse(settings, kwargs={'vm_id': vm.id})),
        2: dict(name='System packages', url=reverse(system_packages, kwargs={'vm_id': vm.id}))
    }

    if request.method == 'POST':
        system_packages_form = SystemPackagesForm(request.POST)
        if system_packages_form.is_valid():
            if ansible_configuraton is not None:
                ansible_configuraton.value = ",".join(system_packages_form.cleaned_data.get('system_packages'))
                ansible_configuraton.save()
            else:
                AnsibleConfiguration.objects.create(vm=vm, key="System Packages",
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
        'system_packages_form': system_packages_form,
        'vm': vm
    })


@login_required
def unix_groups(request, vm_id):
    vm = get_object_or_404(VirtualMachine, pk=vm_id)
    site = privileges_check(vm.site.id, request.user)

    if site is None:
        return HttpResponseForbidden()

    if vm.is_busy:
        return HttpResponseRedirect(reverse('sitesmanagement.views.show', kwargs={'site_id': site.id}))

    breadcrumbs = {
        0: dict(name='Manage Web Server: ' + str(site.name), url=reverse(show, kwargs={'site_id': site.id})),
        1: dict(name='Settings', url=reverse(settings, kwargs={'vm_id': vm.id})),
        2: dict(name='Manage Unix Groups', url=reverse(unix_groups, kwargs={'vm_id': vm.id}))
    }

    return render(request, 'mws/unix_groups.html', {
        'breadcrumbs': breadcrumbs,
        'vm': vm
    })


@login_required
def add_unix_group(request, vm_id):
    vm = get_object_or_404(VirtualMachine, pk=vm_id)
    site = privileges_check(vm.site.id, request.user)

    if site is None:
        return HttpResponseForbidden()

    if vm.is_busy:
        return HttpResponseRedirect(reverse('sitesmanagement.views.show', kwargs={'site_id': site.id}))

    breadcrumbs = {
        0: dict(name='Manage Web Server: ' + str(site.name), url=reverse(show, kwargs={'site_id': site.id})),
        1: dict(name='Settings', url=reverse(settings, kwargs={'vm_id': vm.id})),
        2: dict(name='Manage Unix Groups', url=reverse(unix_groups, kwargs={'vm_id': vm.id})),
        3: dict(name='Add a new Unix Group', url=reverse(add_unix_group, kwargs={'vm_id': vm.id}))
    }

    if request.method == 'POST':
        unix_group_form = UnixGroupForm(request.POST)
        if unix_group_form.is_valid():
            unix_group = unix_group_form.save(commit=False)
            unix_group.vm = vm
            unix_group.save()
            unix_group_form.save_m2m()
            launch_ansible(site)  # to apply these changes to the vm
            return HttpResponseRedirect(reverse(unix_groups, kwargs={'vm_id': vm.id}))
    else:
        unix_group_form = UnixGroupForm()

    return render(request, 'mws/add_unix_group.html', {
        'breadcrumbs': breadcrumbs,
        'vm': vm,
        'unix_group_form': unix_group_form
    })


@login_required
def delete_vm(request, vm_id):
    vm = get_object_or_404(VirtualMachine, pk=vm_id)
    site = privileges_check(vm.site.id, request.user)

    if site is None or vm.primary:
        return HttpResponseForbidden()

    if vm.is_busy:
        return HttpResponseRedirect(reverse('sitesmanagement.views.show', kwargs={'site_id': site.id}))

    #if request.method == 'DELETE':
    vm.delete()  # TODO change this
    return redirect(show, site_id=site.id)

    return HttpResponseForbidden()


@login_required
def unix_group(request, ug_id):
    unix_group = get_object_or_404(UnixGroup, pk=ug_id)
    site = privileges_check(unix_group.vm.site.id, request.user)

    if site is None:
        return HttpResponseForbidden()

    if unix_group.vm.is_busy:
        return HttpResponseRedirect(reverse('sitesmanagement.views.show', kwargs={'site_id': site.id}))

    breadcrumbs = {
        0: dict(name='Manage Web Server: ' + str(site.name), url=reverse(show, kwargs={'site_id': site.id})),
        1: dict(name='Settings', url=reverse(settings, kwargs={'vm_id': unix_group.vm.id})),
        2: dict(name='Manage Unix Groups', url=reverse(unix_groups, kwargs={'vm_id': unix_group.vm.id})),
        3: dict(name='Edit Unix Group', url=reverse('sitesmanagement.views.unix_group',
                                                    kwargs={'ug_id': unix_group.id}))
    }

    if request.method == 'POST':
        unix_group_form = UnixGroupForm(request.POST, instance=unix_group)
        if unix_group_form.is_valid():
            unix_group_form.save()
            launch_ansible(site)  # to apply these changes to the vm
            return HttpResponseRedirect(reverse(unix_groups, kwargs={'vm_id': unix_group.vm.id}))
    else:
        unix_group_form = UnixGroupForm(instance=unix_group)

    return render(request, 'mws/unix_group.html', {
        'breadcrumbs': breadcrumbs,
        'unix_group_form': unix_group_form
    })


@login_required
def delete_unix_group(request, ug_id):
    unix_group = get_object_or_404(UnixGroup, pk=ug_id)
    site = privileges_check(unix_group.vm.site.id, request.user)

    if site is None:
        return HttpResponseForbidden()

    if unix_group.vm.is_busy:
        return HttpResponseRedirect(reverse('sitesmanagement.views.show', kwargs={'site_id': site.id}))

    if request.method == 'DELETE':
        unix_group.delete()
        launch_ansible(site)
        return redirect(unix_groups, vm_id=unix_group.vm.id)

    return HttpResponseForbidden()


@login_required
def power_vm(request, vm_id):
    vm = get_object_or_404(VirtualMachine, pk=vm_id)
    site = privileges_check(vm.site.id, request.user)

    if site is None:
        return HttpResponseForbidden()

    if not vm.is_ready:
        return redirect(reverse(show, kwargs={'site_id': site.id}))

    vm.power_on()

    return redirect(settings, vm_id=vm.id)


@login_required
def reset_vm(request, vm_id):
    vm = get_object_or_404(VirtualMachine, pk=vm_id)
    site = privileges_check(vm.site.id, request.user)

    if site is None:
        return HttpResponseForbidden()

    if not vm.is_ready:
        return HttpResponseRedirect(reverse('sitesmanagement.views.show', kwargs={'site_id': site.id}))

    if vm is None or vm.status != 'ready':
        return redirect(reverse(show, kwargs={'site_id': site.id}))

    if vm.do_reset() is False:
        pass  # TODO add error messages in session if it is False

    return redirect(settings, vm_id=vm.id)


@login_required
def delete_vhost(request, vhost_id):
    vhost = get_object_or_404(Vhost, pk=vhost_id)
    site = privileges_check(vhost.vm.site.id, request.user)

    if site is None:
        return HttpResponseForbidden()

    if vhost.vm.is_busy:
        return HttpResponseRedirect(reverse('sitesmanagement.views.show', kwargs={'site_id': site.id}))

    if request.method == 'DELETE':
        vhost.delete()
        launch_ansible(site)
        return redirect(show, site_id=site.id)

    return HttpResponseForbidden()


@login_required
def domains_management(request, vhost_id):
    vhost = get_object_or_404(Vhost, pk=vhost_id)
    site = privileges_check(vhost.vm.site.id, request.user)

    if site is None:
        return HttpResponseForbidden()

    if vhost.vm.is_busy:
        return HttpResponseRedirect(reverse('sitesmanagement.views.show', kwargs={'site_id': site.id}))

    breadcrumbs = {
        0: dict(name='Manage Web Server: ' + str(site.name), url=reverse(show, kwargs={'site_id': site.id})),
        1: dict(name='Settings', url=reverse(settings, kwargs={'vm_id': vhost.vm.id})),
        2: dict(name='Vhosts Management: %s' % vhost.name, url=reverse(vhosts_management,
                                                                       kwargs={'vm_id': vhost.vm.id})),
        3: dict(name='Domains Management', url=reverse(domains_management, kwargs={'vhost_id': vhost.id}))
    }

    return render(request, 'mws/domains.html', {
        'breadcrumbs': breadcrumbs,
        'vhost': vhost
    })


@login_required
def add_domain(request, vhost_id, socket_error=None):
    vhost = get_object_or_404(Vhost, pk=vhost_id)
    site = privileges_check(vhost.vm.site.id, request.user)

    if site is None:
        return HttpResponseForbidden()

    if vhost.vm.is_busy:
        return HttpResponseRedirect(reverse('sitesmanagement.views.show', kwargs={'site_id': site.id}))

    breadcrumbs = {
        0: dict(name='Manage Web Server: ' + str(site.name), url=reverse(show, kwargs={'site_id': site.id})),
        1: dict(name='Settings', url=reverse(settings, kwargs={'vm_id': vhost.vm.id})),
        2: dict(name='Vhosts Management: %s' % vhost.name, url=reverse(vhosts_management,
                                                                       kwargs={'vm_id': vhost.vm.id})),
        3: dict(name='Domains Management', url=reverse(domains_management, kwargs={'vhost_id': vhost.id})),
        4: dict(name='Add Domain', url=reverse(add_domain, kwargs={'vhost_id': vhost.id}))
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
def certificates(request, vhost_id):
    vhost = get_object_or_404(Vhost, pk=vhost_id)
    site = privileges_check(vhost.vm.site.id, request.user)

    if site is None:
        return HttpResponseForbidden()

    if vhost.vm.is_busy:
        return HttpResponseRedirect(reverse('sitesmanagement.views.show', kwargs={'site_id': site.id}))

    breadcrumbs = {
        0: dict(name='Manage Web Server: ' + str(site.name), url=reverse(show, kwargs={'site_id': site.id})),
        1: dict(name='Settings', url=reverse(settings, kwargs={'vm_id': vhost.vm.id})),
        2: dict(name='Vhosts Management: %s' % vhost.name, url=reverse(vhosts_management,
                                                                       kwargs={'vm_id': vhost.vm.id})),
        3: dict(name='TLS/SSL Certificates', url=reverse(certificates, kwargs={'vhost_id': vhost.id})),
    }

    return render(request, 'mws/certificates.html', {
        'breadcrumbs': breadcrumbs,
        'vhost': vhost,
        'site': site,
    })


@login_required
def set_dn_as_main(request, domain_id):  # TODO remove vhost_id
    domain = get_object_or_404(DomainName, pk=domain_id)
    vhost = domain.vhost
    site = privileges_check(vhost.vm.site.id, request.user)

    if site is None:
        return HttpResponseForbidden()

    if vhost.vm.is_busy:
        return HttpResponseRedirect(reverse('sitesmanagement.views.show', kwargs={'site_id': site.id}))

    if domain not in vhost.domain_names.all():
        return HttpResponseForbidden()

    if request.method == 'POST':
        vhost.main_domain = domain
        vhost.save()
        launch_ansible(site)  # to update the vhost main domain name in the apache configuration

    return HttpResponseRedirect(reverse('sitesmanagement.views.domains_management', kwargs={'vhost_id': vhost.id}))