import bisect
import datetime
import subprocess
from Crypto.Util import asn1
import OpenSSL.crypto
from django.utils import dateparse
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.db import transaction
from django.http import HttpResponseRedirect, HttpResponseForbidden, JsonResponse, HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
import reversion
from ucamlookup import get_group_ids_of_a_user_in_lookup, IbisException, user_in_groups, validate_crsids
from apimws.models import AnsibleConfiguration
from apimws.platforms import PlatformsAPINotWorkingException, new_site_primary_vm, clone_vm
from apimws.utils import email_confirmation, ip_register_api_request, launch_ansible
from mwsauth.utils import get_or_create_group_by_groupid, privileges_check
from sitesmanagement.utils import is_camacuk, get_object_or_None
from .models import SiteForm, DomainNameFormNew, BillingForm, DomainName, NetworkConfig, EmailConfirmation, \
    VirtualMachine, Vhost, VhostForm, Site, UnixGroupForm, UnixGroup
from django.conf import settings as django_settings


@login_required
def index(request):
    try:
        groups_id = get_group_ids_of_a_user_in_lookup(request.user)
    except IbisException:
        groups_id = []

    sites = []
    for group_id in groups_id:
        group = get_or_create_group_by_groupid(group_id)
        sites += group.sites.all()

    sites += request.user.sites.all()

    sites_enabled = filter(lambda site: not site.is_canceled() and not site.is_disabled(), sites)

    sites_disabled = filter(lambda site: not site.is_canceled() and site.is_disabled(), sites)

    sites_authorised = filter(lambda site: not site.is_canceled() and not site.is_disabled(),
                              request.user.sites_auth_as_user.all())

    return render(request, 'index.html', {
        'sites_enabled': sorted(set(sites_enabled)),
        'sites_disabled': sorted(set(sites_disabled)),
        'sites_authorised': sorted(set(sites_authorised)),
        'deactivate_new': NetworkConfig.num_pre_allocated() < 1
    })


@login_required
def new(request):
    if NetworkConfig.num_pre_allocated() < 1:
        return HttpResponseRedirect(reverse('sitesmanagement.views.index'))

    breadcrumbs = {
        0: dict(name='New Manage Web Service server', url=reverse(new))
    }

    # TODO: FIX: if SiteForm's name field is empty then DomainNameForm errors are also shown
    if request.method == 'POST':
        site_form = SiteForm(request.POST, prefix="siteform", user=request.user)
        if site_form.is_valid():

            site = site_form.save(commit=False)
            site.start_date = datetime.date.today()
            site.network_configuration = NetworkConfig.get_free_config()  # TODO raise an error if None
            site.save()

            # Save user that requested the site
            site.users.add(request.user)

            vm = VirtualMachine.objects.create(primary=True, status='requested', site=site)
            new_site_primary_vm.delay(vm)

            if site.email:
                email_confirmation.delay(site)

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
        0: dict(name='Manage Web Service server: ' + str(site.name), url=reverse(show, kwargs={'site_id': site.id})),
        1: dict(name='Manage Web Service account settings',
                url=reverse('sitesmanagement.views.edit', kwargs={'site_id': site.id}))
    }

    if request.method == 'POST':
        site_form = SiteForm(request.POST, user=request.user, instance=site)
        if site_form.is_valid():
            site_form.save()
            if 'email' in site_form.changed_data:
                if site.email:
                    email_confirmation.delay(site)
                    # TODO launch ansible to update webmaster email address in host?
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
        0: dict(name='Manage Web Service server: ' + str(site.name), url=reverse(show, kwargs={'site_id': site.id})),
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
        0: dict(name='Manage Web Service server: ' + str(site.name), url=reverse(show, kwargs={'site_id': site.id})),
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
        0: dict(name='Manage Web Service server: ' + str(site.name), url=reverse(show, kwargs={'site_id': site.id}))
    }

    warning_messages = []
    primary_vm = site.primary_vm

    if primary_vm is not None and primary_vm.status == 'ansible':
        warning_messages.append("Your server is being configured.")

    if site.secondary_vm is not None and site.secondary_vm.status == 'ansible':
        warning_messages.append("Your test server is being configured.")

    if primary_vm is not None:
        if primary_vm.due_update():
            warning_messages.append("Your server is due to an OS update. From %s %.2f to %s %.2f" %
                                    (primary_vm.os_type, primary_vm.os_version, primary_vm.os_type,
                                     django_settings.OS_VERSION[primary_vm.os_type]))
        for vhost in primary_vm.vhosts.all():
            for domain_name in vhost.domain_names.all():
                if domain_name.status == 'requested':
                    warning_messages.append("Your domain name %s has been requested and is under review." %
                                            domain_name.name)

    if not hasattr(site, 'billing'):
        warning_messages.append("No billing details are available, please add them.")

    if site.email:
        try:
            site_email = EmailConfirmation.objects.get(email=site.email, site_id=site.id)
            if site_email.status == 'pending':
                warning_messages.append("Your email '%s' is still unconfirmed, please check your email inbox and "
                                        "click on the link of the email we sent you." % site.email)
        except EmailConfirmation.DoesNotExist:
            pass

    if site.primary_vm is None or site.primary_vm.status == 'requested':
        warning_messages.append("Your request in the Managed Web Service is being processed")

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

    breadcrumbs = {
        0: dict(name='Manage Web Service server: ' + str(site.name), url=reverse(show, kwargs={'site_id': site.id})),
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
        0: dict(name='Manage Web Service server: ' + str(site.name), url=reverse(show, kwargs={'site_id': site.id})),
        1: dict(name='Production and test servers management', url=reverse(clone_vm_view, kwargs={'site_id': site.id}))
    }

    if request.method == 'POST':
        if request.POST.get('primary_vm') == "true":
            clone_vm(site, True)
        if request.POST.get('primary_vm') == "false":
            clone_vm(site, False)

        return redirect(show, site_id=site.id)

    return render(request, 'mws/clone_vm.html', {
        'breadcrumbs': breadcrumbs,
        'site': site,
    })


def privacy(request):
    return render(request, 'privacy.html', {})


@login_required
def vhosts_management(request, vm_id):
    vm = get_object_or_404(VirtualMachine, pk=vm_id)
    site = privileges_check(vm.site.id, request.user)

    if site is None:
        return HttpResponseForbidden()

    if vm.is_busy:
        return HttpResponseRedirect(reverse('sitesmanagement.views.show', kwargs={'site_id': site.id}))

    breadcrumbs = {
        0: dict(name='Manage Web Service server: ' + str(site.name), url=reverse(show, kwargs={'site_id': site.id})),
        1: dict(name='Server settings' if vm.primary else 'Test server settings', url=reverse(settings,
                                                                                              kwargs={'vm_id': vm.id})),
        2: dict(name='Web sites management', url=reverse(vhosts_management, kwargs={'vm_id': vm.id}))
    }

    return render(request, 'mws/vhosts.html', {
        'breadcrumbs': breadcrumbs,
        'vm': vm,
        'site': site,
        'vhost_form': VhostForm()
    })


@login_required
def add_vhost(request, vm_id):
    vm = get_object_or_404(VirtualMachine, pk=vm_id)
    site = privileges_check(vm.site.id, request.user)

    if site is None:
        return HttpResponseForbidden()

    if vm.is_busy:
        return HttpResponseRedirect(reverse('sitesmanagement.views.show', kwargs={'site_id': site.id}))

    if request.method == 'POST':
        vhost_form = VhostForm(request.POST)
        if vhost_form.is_valid():
            vhost = vhost_form.save(commit=False)
            vhost.vm = vm
            vhost.save()
            launch_ansible(vm)  # to create a new vhost configuration file

    return redirect(reverse('sitesmanagement.views.vhosts_management', kwargs={'vm_id': vm.id}))


@login_required
def settings(request, vm_id):
    vm = get_object_or_404(VirtualMachine, pk=vm_id)
    site = privileges_check(vm.site.id, request.user)

    if site is None:
        return HttpResponseForbidden()

    if vm.is_busy:
        return redirect(reverse(show, kwargs={'site_id': site.id}))

    breadcrumbs = {
        0: dict(name='Manage Web Service server: ' + str(site.name), url=reverse(show, kwargs={'site_id': site.id})),
        1: dict(name='Server settings' if vm.primary else 'Test server settings', url=reverse(settings,
                                                                                              kwargs={'vm_id': vm.id}))
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
        return JsonResponse({'error': 'VMNotReady'})
        #return JsonResponse({'error': 'VMNotReady'}, status_code=403) # TODO status_code in JsonResponse doesn't work

    try:
        return JsonResponse({'vm_is_on': vm.is_on()})
    except PlatformsAPINotWorkingException:
        return JsonResponse({'error': 'PlatformsAPINotWorking'})
        #return JsonResponse({'error': 'PlatformsAPINotWorking'}, status_code=500) # TODO status_code doesn't work


@login_required
def system_packages(request, vm_id):
    vm = get_object_or_404(VirtualMachine, pk=vm_id)
    site = privileges_check(vm.site.id, request.user)

    if site is None:
        return HttpResponseForbidden()

    if vm.is_busy:
        return HttpResponseRedirect(reverse('sitesmanagement.views.show', kwargs={'site_id': site.id}))

    ansible_configuraton = get_object_or_None(AnsibleConfiguration, vm=vm, key="system_packages")

    packages_installed = list(int(x) for x in ansible_configuraton.value.split(",")) if ansible_configuraton is not \
                                                                                         None else []

    breadcrumbs = {
        0: dict(name='Manage Web Service server: ' + str(site.name), url=reverse(show, kwargs={'site_id': site.id})),
        1: dict(name='Server settings' if vm.primary else 'Test server settings', url=reverse(settings,
                                                                                              kwargs={'vm_id': vm.id})),
        2: dict(name='System packages', url=reverse(system_packages, kwargs={'vm_id': vm.id}))
    }

    package_number_list = [1,2,3,4] # TODO extract this to settings

    if request.method == 'POST':
        package_number = int(request.POST['package_number'])
        if package_number in package_number_list:
            if packages_installed:
                if package_number in packages_installed:
                    packages_installed.remove(package_number)
                    ansible_configuraton.value = ",".join(str(x) for x in packages_installed)
                    ansible_configuraton.save()
                else:
                    bisect.insort_left(packages_installed, package_number)
                    ansible_configuraton.value = ",".join(str(x) for x in packages_installed)
                    ansible_configuraton.save()
            else:
                ansible_configuraton = AnsibleConfiguration.objects.create(vm=vm, key="system_packages",
                                                                           value=str(package_number))
            launch_ansible(vm)  # to install or delete new/old packages selected by the user
            packages_installed = list(int(x) for x in ansible_configuraton.value.split(",")) if ansible_configuraton \
                                                                                                is not None else []

    return render(request, 'mws/system_packages.html', {
        'breadcrumbs': breadcrumbs,
        'packages_installed': packages_installed,
        'site': site,
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
        0: dict(name='Manage Web Service server: ' + str(site.name), url=reverse(show, kwargs={'site_id': site.id})),
        1: dict(name='Server settings' if vm.primary else 'Test server settings', url=reverse(settings,
                                                                                              kwargs={'vm_id': vm.id})),
        2: dict(name='Manage Unix Groups', url=reverse(unix_groups, kwargs={'vm_id': vm.id}))
    }

    return render(request, 'mws/unix_groups.html', {
        'breadcrumbs': breadcrumbs,
        'site': site,
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
        0: dict(name='Manage Web Service server: ' + str(site.name), url=reverse(show, kwargs={'site_id': site.id})),
        1: dict(name='Server settings' if vm.primary else 'Test server settings', url=reverse(settings,
                                                                                              kwargs={'vm_id': vm.id})),
        2: dict(name='Manage Unix Groups', url=reverse(unix_groups, kwargs={'vm_id': vm.id})),
        3: dict(name='Add a new Unix Group', url=reverse(add_unix_group, kwargs={'vm_id': vm.id}))
    }

    lookup_lists = {
        'unix_users': []  # TODO to be removed once django-ucam-lookup is modified
    }

    if request.method == 'POST':
        unix_group_form = UnixGroupForm(request.POST)
        if unix_group_form.is_valid():

            unix_group = unix_group_form.save(commit=False)
            unix_group.vm = vm
            unix_group.save()

            unix_users = validate_crsids(request.POST.get('unix_users'))
            # TODO If there are no users in the list return an Exception?
            unix_group.users.add(*unix_users)

            launch_ansible(vm)  # to apply these changes to the vm
            return HttpResponseRedirect(reverse(unix_groups, kwargs={'vm_id': vm.id}))
    else:
        unix_group_form = UnixGroupForm()

    return render(request, 'mws/add_unix_group.html', {
        'breadcrumbs': breadcrumbs,
        'site': site,
        'vm': vm,
        'lookup_lists': lookup_lists,  # TODO to be removed once django-ucam-lookup is modified
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

    if request.method == 'DELETE':
        vm.delete()
        return redirect(show, site_id=site.id)

    return HttpResponseForbidden()


@login_required
def unix_group(request, ug_id):
    unix_group_i = get_object_or_404(UnixGroup, pk=ug_id)
    site = privileges_check(unix_group_i.vm.site.id, request.user)

    if site is None:
        return HttpResponseForbidden()

    if unix_group_i.vm.is_busy:
        return HttpResponseRedirect(reverse('sitesmanagement.views.show', kwargs={'site_id': site.id}))

    breadcrumbs = {
        0: dict(name='Manage Web Service server: ' + str(site.name), url=reverse(show, kwargs={'site_id': site.id})),
        1: dict(name='Server settings' if unix_group_i.vm.primary else 'Test server settings',
                url=reverse(settings, kwargs={'vm_id': unix_group_i.vm.id})),
        2: dict(name='Manage Unix Groups', url=reverse(unix_groups, kwargs={'vm_id': unix_group_i.vm.id})),
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

            launch_ansible(unix_group_i.vm)  # to apply these changes to the vm
            return HttpResponseRedirect(reverse(unix_groups, kwargs={'vm_id': unix_group_i.vm.id}))
    else:
        unix_group_form = UnixGroupForm(instance=unix_group_i)

    return render(request, 'mws/unix_group.html', {
        'breadcrumbs': breadcrumbs,
        'lookup_lists': lookup_lists,
        'site': site,
        'vm': unix_group_i.vm,
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
        launch_ansible(unix_group.vm)
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
        return redirect(reverse(show, kwargs={'site_id': site.id}))

    if vm.do_reset() is False:
        pass  # TODO add error messages in session if it is False

    return redirect(settings, vm_id=vm.id)


@login_required
def update_os(request, vm_id):
    vm = get_object_or_404(VirtualMachine, pk=vm_id)
    site = privileges_check(vm.site.id, request.user)

    if site is None:
        return HttpResponseForbidden()

    if not vm.is_ready: # TODO change the button format (disabled) if the vm is not ready
        return redirect(reverse(show, kwargs={'site_id': site.id}))

    # TODO Launch ansible task to update the Operating System

    return HttpResponse('')


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
        launch_ansible(vhost.vm)
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
        0: dict(name='Manage Web Service server: ' + str(site.name), url=reverse(show, kwargs={'site_id': site.id})),
        1: dict(name='Server settings' if vhost.vm.primary else 'Test server settings',
                url=reverse(settings, kwargs={'vm_id': vhost.vm.id})),
        2: dict(name='Web sites management: %s' % vhost.name, url=reverse(vhosts_management,
                                                                       kwargs={'vm_id': vhost.vm.id})),
        3: dict(name='Domain Names management', url=reverse(domains_management, kwargs={'vhost_id': vhost.id}))
    }

    return render(request, 'mws/domains.html', {
        'breadcrumbs': breadcrumbs,
        'vhost': vhost,
        'site': site,
        'vm': vhost.vm,
        'domain_form': DomainNameFormNew()
    })


@login_required
def add_domain(request, vhost_id, socket_error=None):
    vhost = get_object_or_404(Vhost, pk=vhost_id)
    site = privileges_check(vhost.vm.site.id, request.user)

    if site is None:
        return HttpResponseForbidden()

    if vhost.vm.is_busy:
        return HttpResponseRedirect(reverse('sitesmanagement.views.show', kwargs={'site_id': site.id}))

    if request.method == 'POST':
        domain_form = DomainNameFormNew(request.POST)
        if domain_form.is_valid():
            domain_requested = domain_form.save(commit=False)
            if domain_requested.name != '':  # TODO do it after saving a domain request
                if is_camacuk(domain_requested.name):
                    new_domain = DomainName.objects.create(name=domain_requested.name, status='requested',
                                                                 vhost=vhost)
                    ip_register_api_request.delay(new_domain)
                else:
                    new_domain = DomainName.objects.create(name=domain_requested.name, status='accepted', vhost=vhost)
                    if vhost.main_domain is None:
                        vhost.main_domain = new_domain
                        vhost.save()
                launch_ansible(vhost.vm)  # to add the new domain name to the vhost apache configuration
        else:
            breadcrumbs = {
                0: dict(name='Manage Web Service server: ' + str(site.name), url=reverse(show,
                                                                                         kwargs={'site_id': site.id})),
                1: dict(name='Server settings' if vhost.vm.primary else 'Test server settings',
                        url=reverse(settings, kwargs={'vm_id': vhost.vm.id})),
                2: dict(name='Web sites management: %s' % vhost.name, url=reverse(vhosts_management,
                                                                               kwargs={'vm_id': vhost.vm.id})),
                3: dict(name='Domain Names management', url=reverse(domains_management, kwargs={'vhost_id': vhost.id}))
            }

            return render(request, 'mws/domains.html', {
                'breadcrumbs': breadcrumbs,
                'vhost': vhost,
                'site': site,
                'vm': vhost.vm,
                'domain_form': domain_form,
                'error': True
            })

    return redirect(reverse('sitesmanagement.views.domains_management', kwargs={'vhost_id': vhost.id}))


@login_required
def certificates(request, vhost_id):
    vhost = get_object_or_404(Vhost, pk=vhost_id)
    site = privileges_check(vhost.vm.site.id, request.user)

    if site is None:
        return HttpResponseForbidden()

    if vhost.vm.is_busy:
        return HttpResponseRedirect(reverse('sitesmanagement.views.show', kwargs={'site_id': site.id}))

    if not vhost.domain_names.all():
        return redirect(reverse(vhosts_management, kwargs={'vm_id': vhost.vm.id}))

    breadcrumbs = {
        0: dict(name='Manage Web Service server: ' + str(site.name), url=reverse(show, kwargs={'site_id': site.id})),
        1: dict(name='Server settings' if vhost.vm.primary else 'Test server settings',
                url=reverse(settings, kwargs={'vm_id': vhost.vm.id})),
        2: dict(name='Web sites management: %s' % vhost.name, url=reverse(vhosts_management,
                                                                       kwargs={'vm_id': vhost.vm.id})),
        3: dict(name='TLS/SSL Certificate', url=reverse(certificates, kwargs={'vhost_id': vhost.id})),
    }

    error_message = None

    if request.method == 'POST':
        c=OpenSSL.crypto

        if 'cert' in request.FILES:
            try:
                certificates_str = request.FILES['cert'].file.read()
                cert = c.load_certificate(c.FILETYPE_PEM, certificates_str)
            except Exception as e:
                error_message = "The certificate file is invalid"
                # raise ValidationError(e)

        if 'key' in request.FILES and error_message is None:
            try:
                key_str = request.FILES['key'].file.read()
                priv = c.load_privatekey(c.FILETYPE_PEM, key_str)
            except Exception as e:
                error_message = "The key file is invalid"
                # raise ValidationError(e)

        if 'cert' in request.FILES and 'key' in request.FILES and error_message is None:
            try:
                pub = cert.get_pubkey()

                pub_asn1 = c.dump_privatekey(c.FILETYPE_ASN1, pub)
                priv_asn1 = c.dump_privatekey(c.FILETYPE_ASN1, priv)

                pub_der = asn1.DerSequence()
                pub_der.decode(pub_asn1)
                priv_der = asn1.DerSequence()
                priv_der.decode(priv_asn1)

                pub_modulus = pub_der[1]
                priv_modulus = priv_der[1]

                if pub_modulus != priv_modulus:
                    error_message = "The key doesn't match the certificate"
                    # raise ValidationError(e)

            except Exception as e:
                error_message = "The key doesn't match the certificate"
                # raise ValidationError(e)

        if 'cert' in request.FILES and not error_message:
            vhost.certificate = certificates_str
            vhost.save()

    return render(request, 'mws/certificates.html', {
        'breadcrumbs': breadcrumbs,
        'vhost': vhost,
        'vm': vhost.vm,
        'site': site,
        'error_message': error_message
    })


@login_required
def generate_csr(request, vhost_id):
    vhost = get_object_or_404(Vhost, pk=vhost_id)
    site = privileges_check(vhost.vm.site.id, request.user)

    if request.method == 'POST':
        if vhost.main_domain is None:
            breadcrumbs = {
                0: dict(name='Manage Web Service server: ' + str(site.name), url=reverse(show,
                                                                                         kwargs={'site_id': site.id})),
                1: dict(name='Server settings' if vhost.vm.primary else 'Test server settings',
                         url=reverse(settings, kwargs={'vm_id': vhost.vm.id})),
                2: dict(name='Vhosts Management: %s' % vhost.name, url=reverse(vhosts_management,
                                                                               kwargs={'vm_id': vhost.vm.id})),
                3: dict(name='TLS/SSL Certificates', url=reverse(certificates, kwargs={'vhost_id': vhost.id})),
            }

            return render(request, 'mws/certificates.html', {
                'breadcrumbs': breadcrumbs,
                'vhost': vhost,
                'vm': vhost.vm,
                'site': site,
                'error_main_domain': True
            })

        vhost.csr = subprocess.check_output(["openssl", "req", "-new", "-newkey", "rsa:2048", "-nodes", "-keyout",
                                             "/dev/null", "-subj", "/C=GB/CN=%s" % vhost.main_domain.name])
        vhost.save()
        # launch_ansible(vhost.vm) # with a task to create the CSR
        # include all domain names in the common name field in the CSR
        # country is always GB
        # all other parameters/fields are optional and won't appear in the certificate, just ignore them.

    return redirect(reverse(certificates, kwargs={'vhost_id': vhost.id}))


@login_required
def set_dn_as_main(request, domain_id):
    domain = get_object_or_404(DomainName, pk=domain_id)
    vhost = domain.vhost
    site = privileges_check(vhost.vm.site.id, request.user)

    if site is None:
        return HttpResponseForbidden()

    if vhost.vm.is_busy:
        return HttpResponseRedirect(reverse('sitesmanagement.views.show', kwargs={'site_id': site.id}))

    if request.method == 'POST':
        vhost.main_domain = domain
        vhost.save()
        launch_ansible(vhost.vm)  # to update the vhost main domain name in the apache configuration

    return HttpResponseRedirect(reverse('sitesmanagement.views.domains_management', kwargs={'vhost_id': vhost.id}))


@login_required
def delete_dn(request, domain_id):
    domain = get_object_or_404(DomainName, pk=domain_id)
    vhost = domain.vhost
    site = privileges_check(vhost.vm.site.id, request.user)

    if site is None:
        return HttpResponseForbidden()

    if vhost.vm.is_busy:
        return HttpResponseRedirect(reverse('sitesmanagement.views.show', kwargs={'site_id': site.id}))

    if request.method == 'DELETE':
        if is_camacuk(domain.name):
            domain.status = 'to_be_deleted'
            domain.save()
        else:
            domain.delete()
        launch_ansible(vhost.vm)
        return HttpResponseRedirect(reverse('sitesmanagement.views.domains_management', kwargs={'vhost_id': vhost.id}))

    return HttpResponseForbidden()


@login_required
def change_db_root_password(request, vm_id):
    vm = get_object_or_404(VirtualMachine, pk=vm_id)
    site = privileges_check(vm.site.id, request.user)

    if site is None:
        return HttpResponseForbidden()

    if vm.is_busy:
        return HttpResponseRedirect(reverse('sitesmanagement.views.show', kwargs={'site_id': site.id}))

    breadcrumbs = {
        0: dict(name='Manage Web Service server: ' + str(site.name), url=reverse(show, kwargs={'site_id': site.id})),
        1: dict(name='Server settings' if vm.primary else 'Test server settings', url=reverse(settings,
                                                                                              kwargs={'vm_id': vm.id})),
        2: dict(name='Change db root pass', url=reverse(change_db_root_password, kwargs={'vm_id': vm.id})),
    }

    if request.method == 'POST':
        new_root_passwd = request.POST['new_root_passwd']
        # TODO do something
        return HttpResponseRedirect(reverse(settings, kwargs={'vm_id': vm.id}))

    return render(request, 'mws/change_db_root_password.html', {
        'breadcrumbs': breadcrumbs,
        'vm': vm,
        'site': site,
    })


@login_required
def visit_vhost(request, vhost_id):
    vhost = get_object_or_404(Vhost, pk=vhost_id)
    site = privileges_check(vhost.vm.site.id, request.user)

    if site is None:
        return HttpResponseForbidden()

    if vhost.vm.is_busy:
        return HttpResponseRedirect(reverse('sitesmanagement.views.show', kwargs={'site_id': site.id}))

    return redirect("http://"+str(vhost.main_domain.name))


@login_required
def backups(request, vm_id):
    vm = get_object_or_404(VirtualMachine, pk=vm_id)
    site = privileges_check(vm.site.id, request.user)

    if site is None:
        return HttpResponseForbidden()

    if vm.is_busy:
        return HttpResponseRedirect(reverse('sitesmanagement.views.show', kwargs={'site_id': site.id}))

    breadcrumbs = {
        0: dict(name='Manage Web Service server: ' + str(site.name), url=reverse(show, kwargs={'site_id': site.id})),
        1: dict(name='Server settings' if vm.primary else 'Test server settings', url=reverse(settings,
                                                                                              kwargs={'vm_id': vm.id})),
        2: dict(name='Restore backup', url=reverse(backups, kwargs={'vm_id': vm.id})),
    }

    parameters = {
        'breadcrumbs': breadcrumbs,
        'vm': vm,
        'site': site,
        'fromdate': datetime.date.today()-datetime.timedelta(days=30),
        'todate': datetime.date.today()-datetime.timedelta(days=1),
    }

    if request.method == 'POST':
        try:
            backup_date = dateparse.parse_datetime(request.POST['backupdate'])
            if backup_date is None or backup_date > datetime.datetime.now() \
                    or backup_date < (datetime.datetime.now()-datetime.timedelta(days=30)): # TODO or backup_date >= datetime.date.today() ????
                raise ValueError
            launch_ansible(vm) # TODO restore data, once successfully completed restore database data
            version = reversion.get_for_date(vm, backup_date)
            version.revision.revert(delete=True)
            for domain in vm.all_domain_names:
                if domain.status == "requested":
                    last_version = reversion.get_for_object(domain)[0]
                    if last_version.field_dict['id'] != domain.id:
                        raise Exception # TODO change this to a custom exception
                    domain.status = last_version.field_dict['status']
                    domain.save()
        except ValueError:
            parameters['error_message'] = "Incorrect date"
            return render(request, 'mws/backups.html', parameters)
        except Exception as e:
            parameters['error_message'] = str(e)
            return render(request, 'mws/backups.html', parameters)

        # TODO do something + check that dates are correct
        return HttpResponseRedirect(reverse(show, kwargs={'site_id': site.id}))

    return render(request, 'mws/backups.html', parameters)
