"""Views(Controllers) for other purposes not in other files"""

import bisect
import datetime
from django.conf import settings
from django.utils import dateparse
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, HttpResponseForbidden, JsonResponse, HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from apimws.ansible import launch_ansible, ansible_change_mysql_root_pwd, restore_snapshot
from apimws.models import AnsibleConfiguration
from apimws.vm import VMAPINotWorkingException, clone_vm, VMAPIFailure
from mwsauth.utils import privileges_check
from sitesmanagement.forms import BillingForm, SnapshotForm
from sitesmanagement.utils import get_object_or_None
from sitesmanagement.models import Service, Snapshot


@login_required
def billing_management(request, site_id):
    site = privileges_check(site_id, request.user)

    if site is None:
        return HttpResponseForbidden()

    breadcrumbs = {
        0: dict(name='Manage Web Service site: ' + str(site.name), url=site.get_absolute_url()),
        1: dict(name='Billing', url=reverse(billing_management, kwargs={'site_id': site.id}))
    }

    if request.method == 'POST':
        if hasattr(site, 'billing'):
            billing_form = BillingForm(request.POST, request.FILES, instance=site.billing)
            if billing_form.is_valid():
                billing_form.save()
                return redirect(site)
        else:
            billing_form = BillingForm(request.POST, request.FILES)
            if billing_form.is_valid():
                billing = billing_form.save(commit=False)
                billing.site = site
                billing.save()
                return redirect(site)
    elif hasattr(site, 'billing'):
        billing_form = BillingForm(instance=site.billing)
    else:
        billing_form = BillingForm()

    return render(request, 'mws/billing.html', {
        'breadcrumbs': breadcrumbs,
        'site': site,
        'billing_form': billing_form,
        'cost': settings.YEAR_COST
    })


@login_required
def clone_vm_view(request, site_id):
    if getattr(settings, 'DEMO', False):
        return HttpResponseRedirect(reverse('listsites'))
    site = privileges_check(site_id, request.user)

    if site is None:
        return HttpResponseForbidden()

    if not site.is_ready:
        return redirect(site)

    breadcrumbs = {
        0: dict(name='Manage Web Service site: ' + str(site.name), url=site.get_absolute_url()),
        1: dict(name='Production and test servers management', url=reverse(clone_vm_view, kwargs={'site_id': site.id}))
    }

    if request.method == 'POST':
        if request.POST.get('primary_vm') == "true":
            clone_vm(site, True)
        if request.POST.get('primary_vm') == "false":
            clone_vm(site, False)

        return redirect(site)

    return render(request, 'mws/clone_vm.html', {
        'breadcrumbs': breadcrumbs,
        'site': site,
    })


def privacy(request):
    return render(request, 'privacy.html', {})


@login_required
def service_settings(request, service_id):
    service = get_object_or_404(Service, pk=service_id)
    site = privileges_check(service.site.id, request.user)

    if site is None:
        return HttpResponseForbidden()

    if service.is_busy:
        return redirect(site)

    breadcrumbs = {
        0: dict(name='Manage Web Service site: ' + str(site.name), url=site.get_absolute_url()),
        1: dict(name='Server settings' if service.primary else 'Test server settings',
                url=reverse(service_settings, kwargs={'service_id': service.id}))
    }

    return render(request, 'mws/settings.html', {
        'breadcrumbs': breadcrumbs,
        'site': site,
        'service': service,
        'DEMO': getattr(settings, 'DEMO', False)
    })


@login_required
def check_vm_status(request, service_id):
    service = get_object_or_404(Service, pk=service_id)
    site = privileges_check(service.site.id, request.user)

    if site is None:
        return HttpResponseForbidden()

    if not service or not service.active or service.is_busy:
        return JsonResponse({'error': 'VMNotReady'})
        # return JsonResponse({'error': 'VMNotReady'}, status_code=403) # TODO status_code in JsonResponse doesn't work

    try:
        return JsonResponse({'service_is_on': service.is_on()})
    except VMAPINotWorkingException:
        return JsonResponse({'error': 'VMAPINotWorking'})
        # return JsonResponse({'error': 'VMAPINotWorking'}, status_code=500) # TODO status_code doesn't work
    except VMAPIFailure:
        return JsonResponse({'error': 'VMAPIFailure'})
    except Exception:
        return JsonResponse({'error': 'Exception'})


@login_required
def system_packages(request, service_id):
    if getattr(settings, 'DEMO', False):
        return HttpResponseRedirect(reverse('listsites'))
    service = get_object_or_404(Service, pk=service_id)
    site = privileges_check(service.site.id, request.user)

    if site is None:
        return HttpResponseForbidden()

    if not service or not service.active or service.is_busy:
        return redirect(site)

    ansible_configuraton = get_object_or_None(AnsibleConfiguration, service=service, key="system_packages") \
                           or AnsibleConfiguration.objects.create(service=service, key="system_packages", value="")

    packages_installed = list(int(x) for x in ansible_configuraton.value.split(",")) \
        if ansible_configuraton.value != '' else []

    breadcrumbs = {
        0: dict(name='Manage Web Service site: ' + str(site.name), url=site.get_absolute_url()),
        1: dict(name='Server settings' if service.primary else 'Test server settings',
                url=reverse(service_settings, kwargs={'service_id': service.id})),
        2: dict(name='System packages', url=reverse(system_packages, kwargs={'service_id': service.id}))
    }

    package_number_list = [1, 2, 3, 4]  # TODO extract this to settings

    if request.method == 'POST':
        package_number = int(request.POST['package_number'])
        if package_number in package_number_list:
            if package_number in packages_installed:
                packages_installed.remove(package_number)
                ansible_configuraton.value = ",".join(str(x) for x in packages_installed)
                ansible_configuraton.save()
            else:
                bisect.insort_left(packages_installed, package_number)
                ansible_configuraton.value = ",".join(str(x) for x in packages_installed)
                ansible_configuraton.save()

            launch_ansible(service)  # to install or delete new/old packages selected by the user

    return render(request, 'mws/system_packages.html', {
        'breadcrumbs': breadcrumbs,
        'packages_installed': packages_installed,
        'site': site,
        'service': service
    })


@login_required
def delete_vm(request, service_id):
    service = get_object_or_404(Service, pk=service_id)
    site = privileges_check(service.site.id, request.user)

    if site is None or service.primary:
        return HttpResponseForbidden()

    if not service or not service.active or service.is_busy:
        return redirect(site)

    if request.method == 'DELETE':
        for vm in service.virtual_machines.all():
            vm.delete()
        return redirect(site)

    return HttpResponseForbidden()


@login_required
def power_vm(request, service_id):
    service = get_object_or_404(Service, pk=service_id)
    site = privileges_check(service.site.id, request.user)

    if site is None:
        return HttpResponseForbidden()

    if not service or not service.active or service.is_busy:
        return redirect(site)

    service.power_on()

    return redirect(service_settings, service_id=service.id)


@login_required
def reset_vm(request, service_id):
    service = get_object_or_404(Service, pk=service_id)
    site = privileges_check(service.site.id, request.user)

    if site is None:
        return HttpResponseForbidden()

    if not service or not service.active or service.is_busy:
        return redirect(site)

    if service.do_reset() is False:
        pass  # TODO add error messages in session if it is False

    return redirect(service_settings, service_id=service.id)


@login_required
def update_os(request, service_id):
    if getattr(settings, 'DEMO', False):
        return HttpResponseRedirect(reverse('listsites'))
    service = get_object_or_404(Service, pk=service_id)
    site = privileges_check(service.site.id, request.user)

    if site is None:
        return HttpResponseForbidden()

    if not service or not service.active or service.is_busy:
    # TODO change the button format (disabled) if the vm is not ready
        return redirect(site)

    # TODO 1) Warn about the secondary VM if exists
    # TODO 2) Delete secondary VM if exists
    # TODO 3) Create a new VM with the new OS and launch an ansible task to restore the state of the DB
    # TODO 4) Put it as a secondary VM?

    return HttpResponse('')


@login_required
def change_db_root_password(request, service_id):
    if getattr(settings, 'DEMO', False):
        return HttpResponseRedirect(reverse('listsites'))
    service = get_object_or_404(Service, pk=service_id)
    site = privileges_check(service.site.id, request.user)

    if site is None:
        return HttpResponseForbidden()

    if not service or not service.active or service.is_busy:
        return redirect(site)

    breadcrumbs = {
        0: dict(name='Manage Web Service site: ' + str(site.name), url=site.get_absolute_url()),
        1: dict(name='Server settings' if service.primary else 'Test server settings',
                url=reverse(service_settings, kwargs={'service_id': service.id})),
        2: dict(name='Change db root pass', url=reverse(change_db_root_password, kwargs={'service_id': service.id})),
    }

    if request.method == 'POST':
        if request.POST.get('typepost') == "Delete temporal mySQL root password":
            AnsibleConfiguration.objects.filter(service=service, key="mysql_root_password").delete()
        else:
            ansibleconf, created = AnsibleConfiguration.objects.get_or_create(service=service,
                                                                              key="mysql_root_password")
            ansibleconf.value = "Resetting"
            ansibleconf.save()
            ansible_change_mysql_root_pwd.delay(service)
            return HttpResponseRedirect(reverse(service_settings, kwargs={'service_id': service.id}))

    ansibleconf = AnsibleConfiguration.objects.filter(service=service, key="mysql_root_password")
    ansibleconf = ansibleconf[0].value if ansibleconf else None

    return render(request, 'mws/change_db_root_password.html', {
        'breadcrumbs': breadcrumbs,
        'service': service,
        'site': site,
        'ansibleconf': ansibleconf,
    })


@login_required
def backups(request, service_id):
    service = get_object_or_404(Service, pk=service_id)
    site = privileges_check(service.site.id, request.user)

    if site is None:
        return HttpResponseForbidden()

    if not service or not service.active or service.is_busy:
        return redirect(site)

    breadcrumbs = {
        0: dict(name='Manage Web Service site: ' + str(site.name), url=site.get_absolute_url()),
        1: dict(name='Server settings' if service.primary else 'Test server settings',
                url=reverse(service_settings, kwargs={'service_id': service.id})),
        2: dict(name='Restore backup', url=reverse(backups, kwargs={'service_id': service.id})),
    }

    fromdate = get_object_or_None(AnsibleConfiguration, service=service, key="backup_first_date")
    if fromdate:
        fromdate = datetime.datetime.strptime(fromdate.value, '%Y-%m-%d').date()
    else:
        fromdate =  datetime.date.today()-datetime.timedelta(days=30)
    if fromdate < site.start_date+datetime.timedelta(days=1):
        fromdate = site.start_date+datetime.timedelta(days=1)

    parameters = {
        'breadcrumbs': breadcrumbs,
        'service': service,
        'site': site,
        'fromdate': fromdate,
        'todate': datetime.date.today()-datetime.timedelta(days=1),
        'snapshot_form': SnapshotForm(),
        'error_message_snap': request.GET['error_message'] if 'error_message' in request.GET else None,
        'limit_snaps': Snapshot.objects.filter(service=service).count() >= 2
    }

    if request.method == 'POST':
        try:
            backup_date = dateparse.parse_date(request.POST['backupdate'])
            if backup_date is None or backup_date > datetime.date.today() or backup_date < fromdate:
                raise ValueError
            if 'snapshot_id' in request.POST:
                snapshot = Snapshot.objects.get(id=request.POST['snapshot_id'], service=service)
                restore_snapshot.delay(service, snapshot.name)
            else:
                restore_snapshot.delay(service, backup_date.strftime("%Y-%m-%d"))
        except ValueError:
            parameters['error_message'] = "Incorrect date"
            return render(request, 'mws/backups.html', parameters)
        except Exception as e:
            parameters['error_message'] = str(e)
            return render(request, 'mws/backups.html', parameters)
        return redirect(site)

    return render(request, 'mws/backups.html', parameters)


@login_required
def apache_modules(request, service_id):
    service = get_object_or_404(Service, pk=service_id)
    site = privileges_check(service.site.id, request.user)

    if site is None:
        return HttpResponseForbidden()

    if not service or not service.active or service.is_busy:
        return redirect(site)

    breadcrumbs = {
        0: dict(name='Manage Web Service site: ' + str(site.name), url=site.get_absolute_url()),
        1: dict(name='Server settings' if service.primary else 'Test server settings',
                url=reverse(service_settings, kwargs={'service_id': service.id})),
        2: dict(name='Apache modules', url=reverse(apache_modules, kwargs={'service_id': service.id})),
    }

    from apimws.forms import ApacheModuleForm

    parameters = {
        'breadcrumbs': breadcrumbs,
        'service': service,
        'site': site,
        'form': ApacheModuleForm(initial={'apache_modules': service.apache_modules.values_list('name', flat=True)}),
    }

    if request.method == 'POST':
        f = ApacheModuleForm(request.POST)
        if f.is_valid():
            service.apache_modules = f.cleaned_data['apache_modules']
            service.save()
            launch_ansible(service)

    return render(request, 'mws/apache.html', parameters)


@login_required
def php_libs(request, service_id):
    service = get_object_or_404(Service, pk=service_id)
    site = privileges_check(service.site.id, request.user)

    if site is None:
        return HttpResponseForbidden()

    if not service or not service.active or service.is_busy:
        return redirect(site)

    breadcrumbs = {
        0: dict(name='Manage Web Service site: ' + str(site.name), url=site.get_absolute_url()),
        1: dict(name='Server settings' if service.primary else 'Test server settings',
                url=reverse(service_settings, kwargs={'service_id': service.id})),
        2: dict(name='PHP Libraries', url=reverse(php_libs, kwargs={'service_id': service.id})),
    }

    from apimws.forms import PHPLibForm

    parameters = {
        'breadcrumbs': breadcrumbs,
        'service': service,
        'site': site,
        'form': PHPLibForm(initial={'php_libs': service.php_libs.values_list('name', flat=True)}),
    }

    if request.method == 'POST':
        f = PHPLibForm(request.POST)
        if f.is_valid():
            service.php_libs = f.cleaned_data['php_libs']
            service.save()
            launch_ansible(service)

    return render(request, 'mws/phplibs.html', parameters)
