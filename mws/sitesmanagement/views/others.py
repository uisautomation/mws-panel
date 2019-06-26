"""Views(Controllers) for other purposes not in other files"""

import json
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, HttpResponseForbidden, HttpResponse, HttpResponseNotFound
from django.shortcuts import render, get_object_or_404, redirect
from django.utils.encoding import smart_str
from django.core.mail import EmailMessage
from apimws.ansible import launch_ansible, ansible_change_mysql_root_pwd
from apimws.models import AnsibleConfiguration, PHPLib, QueueEntry
from apimws.vm import clone_vm_api_call
from apimws.views import post_installOS
from mwsauth.utils import privileges_check
from sitesmanagement.forms import BillingForm
from sitesmanagement.models import Service, Billing, Site, ServerType
from sitesmanagement.views.sites import warning_messages


@login_required
def billing_management(request, site_id):
    site = privileges_check(site_id, request.user)

    if site is None:
        return HttpResponseForbidden()

    breadcrumbs = {
        0: dict(name='Managed Web Service server: ' + str(site.name), url=site.get_absolute_url()),
        1: dict(name='Billing', url=reverse('billing_management', kwargs={'site_id': site.id}))
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
        'sidebar_messages': warning_messages(site),
        'cost': ServerType.objects.get(id=1).price
    })


@login_required
def clone_vm_view(request, site_id):
    site = privileges_check(site_id, request.user)

    if site is None:
        return HttpResponseForbidden()

    can_upgrade = False
    is_queued = False
    if settings.MAX_PENDING_UPGRADES:
        pending_upgrades = len([x for x in Service.objects.filter(type='test').prefetch_related('virtual_machines') if x.active])
        if pending_upgrades < settings.MAX_PENDING_UPGRADES:
            can_upgrade = True
        else:
            if not hasattr(site,'queueentry'):
                QueueEntry.objects.create(site=site)
            else:
                is_queued = True

    breadcrumbs = {
        0: dict(name='Managed Web Service server: ' + str(site.name), url=site.get_absolute_url()),
        1: dict(name='Production and test servers management', url=reverse(clone_vm_view, kwargs={'site_id': site.id}))
    }

    if request.method == 'POST':
        if site.is_ready and site.test_service:
            clone_vm_api_call.delay(site)
            messages.info(request, 'The test server is being created. This will usually take around 10 minutes. You will need to refresh the page.')
        elif not site.is_ready:
            messages.error(request, 'The test server cannot be created while the production server is being configured.')
        elif not site.test_service:
            messages.error(request, 'The test server cannot be created at this moment, please contact mws-support@uis.cam.ac.uk')
        return redirect(site)

    return render(request, 'mws/clone_vm.html', {
        'breadcrumbs': breadcrumbs,
        'site': site,
        'can_upgrade': can_upgrade,
        'is_queued': is_queued,
    })


def privacy(request):
    return render(request, 'privacy.html', {})


def termsconds(request):
    return render(request, 'tcs.html', {})


@login_required
def service_status(request, service_id):
    service = get_object_or_404(Service, pk=service_id)
    site = privileges_check(service.site.id, request.user)

    if site is None:
        return HttpResponseForbidden()

    if site.production_service.is_busy and site.test_service.is_busy:
        status = 'busy'
    elif site.production_service.is_busy:
        status = 'prod'
    elif site.test_service.is_busy:
        status = 'test'
    else:
        status = 'ready'
    return HttpResponse(json.dumps({'status': status}), content_type='application/json')


@login_required
def service_settings(request, service_id):
    service = get_object_or_404(Service, pk=service_id)
    site = privileges_check(service.site.id, request.user)

    if site is None:
        return HttpResponseForbidden()

    if service.is_busy:
        return redirect(site)

    breadcrumbs = {
        0: dict(name='Managed Web Service server: ' + str(site.name), url=site.get_absolute_url()),
        1: dict(name='Server settings' if service.primary else 'Test server settings',
                url=reverse(service_settings, kwargs={'service_id': service.id}))
    }

    return render(request, 'mws/settings.html', {
        'breadcrumbs': breadcrumbs,
        'site': site,
        'service': service,
        'sidebar_messages': warning_messages(site),
    })


@login_required
def delete_vm(request, service_id):
    service = get_object_or_404(Service, pk=service_id)
    site = privileges_check(service.site.id, request.user)

    if site is None or service.primary:
        return HttpResponseForbidden()

    if not service or not service.active or service.is_busy:
        return redirect(site)

    if request.method == 'POST':
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
        messages.error(request, 'Any of the two server is busy during configuration, wait until both of them are ready')
        return redirect(site)

    if request.method == 'POST':
        if service.do_reset():
            messages.success(request, "Your server will be restarted shortly")
        else:
            messages.error(request, "Your server couldn't be restarted")
    else:
        messages.error(request, "An error happened")

    return redirect(site)


@login_required
def change_db_root_password(request, service_id):
    service = get_object_or_404(Service, pk=service_id)
    site = privileges_check(service.site.id, request.user)

    if site is None:
        return HttpResponseForbidden()

    if (service.operating_system == 'stretch') \
            or not service or not service.active or service.is_busy:
        return redirect(site)

    breadcrumbs = {
        0: dict(name='Managed Web Service server: ' + str(site.name), url=site.get_absolute_url()),
        1: dict(name='Server settings' if service.primary else 'Test server settings',
                url=reverse(service_settings, kwargs={'service_id': service.id})),
        2: dict(name='Change db root pass', url=reverse(change_db_root_password, kwargs={'service_id': service.id})),
    }

    if request.method == 'POST':
        if request.POST.get('typepost') == "Delete temporary mySQL root password":
            AnsibleConfiguration.objects.filter(service=service, key="mysql_root_password").delete()
        else:
            ansibleconf, created = AnsibleConfiguration.objects.get_or_create(service=service,
                                                                              key="mysql_root_password")
            ansibleconf.value = "Resetting"
            ansibleconf.save()
            ansible_change_mysql_root_pwd.delay(service)
            return HttpResponseRedirect(reverse(change_db_root_password, kwargs={'service_id': service.id}))

    ansibleconf = AnsibleConfiguration.objects.filter(service=service, key="mysql_root_password")
    ansibleconf = ansibleconf[0].value if ansibleconf else None

    return render(request, 'mws/change_db_root_password.html', {
        'breadcrumbs': breadcrumbs,
        'service': service,
        'site': site,
        'sidebar_messages': warning_messages(site),
        'ansibleconf': ansibleconf,
    })


# @login_required
# def apache_modules(request, service_id):
#     service = get_object_or_404(Service, pk=service_id)
#     site = privileges_check(service.site.id, request.user)
#
#     if site is None:
#         return HttpResponseForbidden()
#
#     if not service or not service.active or service.is_busy:
#         return redirect(site)
#
#     breadcrumbs = {
#         0: dict(name='Managed Web Service server: ' + str(site.name), url=site.get_absolute_url()),
#         1: dict(name='Server settings' if service.primary else 'Test server settings',
#                 url=reverse(service_settings, kwargs={'service_id': service.id})),
#         2: dict(name='Apache modules', url=reverse(apache_modules, kwargs={'service_id': service.id})),
#     }
#
#     from apimws.forms import ApacheModuleForm
#
#     parameters = {
#         'breadcrumbs': breadcrumbs,
#         'service': service,
#         'site': site,
#         'sidebar_messages': warning_messages(site),
#         'form': ApacheModuleForm(initial={
#             'apache_modules': list(service.apache_modules.values_list('name', flat=True))
#         }),
#     }
#
#     if request.method == 'POST':
#         f = ApacheModuleForm(request.POST)
#         if f.is_valid():
#             service.apache_modules.set(
#                 ApacheModule.objects.filter(
#                     name__in=f.cleaned_data['apache_modules']).all(),
#                 clear=True
#             )
#             service.save()
#             launch_ansible(service)
#
#     return render(request, 'mws/apache.html', parameters)


@login_required
def php_libs(request, service_id):
    service = get_object_or_404(Service, pk=service_id)
    site = privileges_check(service.site.id, request.user)

    if site is None:
        return HttpResponseForbidden()

    if not service or not service.active or service.is_busy:
        return redirect(site)

    breadcrumbs = {
        0: dict(name='Managed Web Service server: ' + str(site.name), url=site.get_absolute_url()),
        1: dict(name='Server settings' if service.primary else 'Test server settings',
                url=reverse(service_settings, kwargs={'service_id': service.id})),
        2: dict(name='PHP Libraries', url=reverse(php_libs, kwargs={'service_id': service.id})),
    }

    from apimws.forms import PHPLibForm

    parameters = {
        'breadcrumbs': breadcrumbs,
        'service': service,
        'site': site,
        'sidebar_messages': warning_messages(site),
        'form': PHPLibForm(initial={
            'php_libs': list(service.php_libs.values_list('name', flat=True))
        }, service=service),
    }

    if request.method == 'POST':
        f = PHPLibForm(request.POST, service=service)
        if f.is_valid():
            service.php_libs.set(
                PHPLib.objects.filter(name__in=f.cleaned_data['php_libs']).all(),
                clear=True
            )
            service.save()
            launch_ansible(service)

    return render(request, 'mws/phplibs.html', parameters)


def po_file_serve(request, filename):
    billing = Billing.objects.filter(purchase_order='billing/%s' % filename)
    if billing.exists() and ((request.user in billing[0].site.list_of_admins()) or request.user.is_superuser):
        pofile = billing[0].purchase_order
        response = HttpResponse(pofile.read(), content_type='application/zip')
        response['Content-Disposition'] = 'attachment; filename=%s' % smart_str(filename)
        response['Content-Length'] = pofile.tell()
        return response
    else:
        return HttpResponseNotFound()


@login_required
def quarantine(request, service_id):
    service = get_object_or_404(Service, pk=service_id)
    site = privileges_check(service.site.id, request.user)

    if site is None:
        return HttpResponseForbidden()

    if not service or not service.active or service.is_busy:
        return redirect(site)

    breadcrumbs = {
        0: dict(name='Managed Web Service server: ' + str(site.name), url=site.get_absolute_url()),
        1: dict(name='Server settings' if service.primary else 'Test server settings',
                url=reverse(service_settings, kwargs={'service_id': service.id})),
        2: dict(name='Quarantine', url=reverse(quarantine, kwargs={'service_id': service.id})),
    }

    parameters = {
        'breadcrumbs': breadcrumbs,
        'service': service,
        'site': site,
        'sidebar_messages': warning_messages(site),
    }

    if request.method == 'POST' and not site.is_admin_suspended():
        if request.POST['quarantine'] == "Quarantine":
            service.quarantined = True
        else:
            service.quarantined = False
        service.save()
        launch_ansible(service)
        return redirect(site)

    return render(request, 'mws/quarantine.html', parameters)


@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_email_list(request):
    return render(request, 'mws/admin/email_list.html',
                  {'site_list': Site.objects.filter(deleted=False, preallocated=False, end_date__isnull=True)})


@login_required
def switch_services(request, site_id):
    '''This function swiches the production and test services'''
    site = get_object_or_404(Site, pk=site_id)
    site = privileges_check(site.id, request.user)

    if site is None:
        return HttpResponseForbidden()

    if site.switch_services():
        return redirect(site)
    else:
        messages.error(request, 'An error happened while trying to switch the test server with the production server')
        return redirect(site)


@login_required
def resync(request, site_id):
    '''This function syncs production file system with the test one'''
    site = get_object_or_404(Site, pk=site_id)
    site = privileges_check(site.id, request.user)

    if not site.is_ready:
        messages.error(request, 'Any of the two server is busy during configuration, wait until both of them are ready')
        return redirect(site)

    if request.method == 'POST':
        post_installOS.delay(site.test_service, initial=False)
    messages.info(request, 'The filesystem started to synchronise')
    return redirect(site)
