import bisect
import datetime
import logging
import subprocess
from Crypto.Util import asn1
import OpenSSL.crypto
from django.core.files.temp import NamedTemporaryFile
from django.utils import dateparse
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, HttpResponseForbidden, JsonResponse, HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
import reversion
from apimws.ansible import launch_ansible
from apimws.models import AnsibleConfiguration
from apimws.platforms import PlatformsAPINotWorkingException, clone_vm, PlatformsAPIFailure
from mwsauth.utils import privileges_check
from sitesmanagement.utils import get_object_or_None
from sitesmanagement.models import BillingForm, Vhost, Service


@login_required
def billing_management(request, site_id):
    site = privileges_check(site_id, request.user)

    if site is None:
        return HttpResponseForbidden()

    breadcrumbs = {
        0: dict(name='Manage Web Service server: ' + str(site.name), url=reverse('sitesmanagement.views.show',
                                                                                 kwargs={'site_id': site.id})),
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
        0: dict(name='Manage Web Service server: ' + str(site.name), url=reverse('sitesmanagement.views.show',
                                                                                 kwargs={'site_id': site.id})),
        1: dict(name='Production and test servers management', url=reverse(clone_vm_view, kwargs={'site_id': site.id}))
    }

    if request.method == 'POST':
        if request.POST.get('primary_vm') == "true":
            clone_vm(site, True)
        if request.POST.get('primary_vm') == "false":
            clone_vm(site, False)

        return redirect('sitesmanagement.views.show', site_id=site.id)

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
        return redirect(reverse('sitesmanagement.views.show', kwargs={'site_id': site.id}))

    breadcrumbs = {
        0: dict(name='Manage Web Service server: ' + str(site.name), url=reverse('sitesmanagement.views.show',
                                                                                 kwargs={'site_id': site.id})),
        1: dict(name='Server settings' if service.primary else 'Test server settings',
                url=reverse(service_settings, kwargs={'service_id': service.id}))
    }

    return render(request, 'mws/settings.html', {
        'breadcrumbs': breadcrumbs,
        'site': site,
        'service': service,
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
    except PlatformsAPINotWorkingException:
        return JsonResponse({'error': 'PlatformsAPINotWorking'})
        # return JsonResponse({'error': 'PlatformsAPINotWorking'}, status_code=500) # TODO status_code doesn't work
    except PlatformsAPIFailure:
        return JsonResponse({'error': 'PlatformsAPIFailure'})
    except Exception:
        return JsonResponse({'error': 'Exception'})


@login_required
def system_packages(request, service_id):
    service = get_object_or_404(Service, pk=service_id)
    site = privileges_check(service.site.id, request.user)

    if site is None:
        return HttpResponseForbidden()

    if not service or not service.active or service.is_busy:
        return HttpResponseRedirect(reverse('sitesmanagement.views.show', kwargs={'site_id': site.id}))

    ansible_configuraton = get_object_or_None(AnsibleConfiguration, service=service, key="system_packages") \
                           or AnsibleConfiguration.objects.create(service=service, key="system_packages", value="")

    packages_installed = list(int(x) for x in ansible_configuraton.value.split(",")) \
        if ansible_configuraton.value != '' else []

    breadcrumbs = {
        0: dict(name='Manage Web Service server: ' + str(site.name), url=reverse('sitesmanagement.views.show',
                                                                                 kwargs={'site_id': site.id})),
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
        return HttpResponseRedirect(reverse('sitesmanagement.views.show', kwargs={'site_id': site.id}))

    if request.method == 'DELETE':
        service.delete()
        return redirect('sitesmanagement.views.show', site_id=site.id)

    return HttpResponseForbidden()


@login_required
def power_vm(request, service_id):
    service = get_object_or_404(Service, pk=service_id)
    site = privileges_check(service.site.id, request.user)

    if site is None:
        return HttpResponseForbidden()

    if not service or not service.active or service.is_busy:
        return redirect(reverse('sitesmanagement.views.show', kwargs={'site_id': site.id}))

    service.power_on()

    return redirect(service_settings, service_id=service.id)


@login_required
def reset_vm(request, service_id):
    service = get_object_or_404(Service, pk=service_id)
    site = privileges_check(service.site.id, request.user)

    if site is None:
        return HttpResponseForbidden()

    if not service or not service.active or service.is_busy:
        return redirect(reverse('sitesmanagement.views.show', kwargs={'site_id': site.id}))

    if service.do_reset() is False:
        pass  # TODO add error messages in session if it is False

    return redirect(service_settings, service_id=service.id)


@login_required
def update_os(request, service_id):
    service = get_object_or_404(Service, pk=service_id)
    site = privileges_check(service.site.id, request.user)

    if site is None:
        return HttpResponseForbidden()

    if not service or not service.active or service.is_busy:
    # TODO change the button format (disabled) if the vm is not ready
        return redirect(reverse('sitesmanagement.views.show', kwargs={'site_id': site.id}))

    # TODO 1) Warn about the secondary VM if exists
    # TODO 2) Delete secondary VM if exists
    # TODO 3) Create a new VM with the new OS and launch an ansible task to restore the state of the DB
    # TODO 4) Put it as a secondary VM?

    return HttpResponse('')


@login_required
def certificates(request, vhost_id):
    vhost = get_object_or_404(Vhost, pk=vhost_id)
    site = privileges_check(vhost.service.site.id, request.user)
    service = vhost.service

    if site is None:
        return HttpResponseForbidden()

    if not service or not service.active or service.is_busy:
        return HttpResponseRedirect(reverse('sitesmanagement.views.show', kwargs={'site_id': site.id}))

    if not vhost.domain_names.all():
        return redirect(reverse('sitesmanagement.views.vhosts_management', kwargs={'service_id': vhost.service.id}))

    breadcrumbs = {
        0: dict(name='Manage Web Service server: ' + str(site.name), url=reverse('sitesmanagement.views.show',
                                                                                 kwargs={'site_id': site.id})),
        1: dict(name='Server settings' if vhost.service.primary else 'Test server settings',
                url=reverse(service_settings, kwargs={'service_id': vhost.service.id})),
        2: dict(name='Web sites management: %s' % vhost.name,
                url=reverse('sitesmanagement.views.vhosts_management', kwargs={'service_id': vhost.service.id})),
        3: dict(name='TLS/SSL Certificate', url=reverse(certificates, kwargs={'vhost_id': vhost.id})),
    }

    error_message = None

    if request.method == 'POST':
        c = OpenSSL.crypto

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
        'service': vhost.service,
        'site': site,
        'error_message': error_message
    })


@login_required
def generate_csr(request, vhost_id):
    vhost = get_object_or_404(Vhost, pk=vhost_id)
    site = privileges_check(vhost.service.site.id, request.user)

    if request.method == 'POST':
        if vhost.main_domain is None:
            breadcrumbs = {
                0: dict(name='Manage Web Service server: ' + str(site.name), url=reverse('sitesmanagement.views.show',
                                                                                         kwargs={'site_id': site.id})),
                1: dict(name='Server settings' if vhost.service.primary else 'Test server settings',
                        url=reverse(service_settings, kwargs={'service_id': vhost.service.id})),
                2: dict(name='Vhosts Management: %s' % vhost.name,
                        url=reverse('sitesmanagement.views.vhosts_management',
                                    kwargs={'service_id': vhost.service.id})),
                3: dict(name='TLS/SSL Certificates', url=reverse(certificates, kwargs={'vhost_id': vhost.id})),
            }

            return render(request, 'mws/certificates.html', {
                'breadcrumbs': breadcrumbs,
                'vhost': vhost,
                'service': vhost.service,
                'site': site,
                'error_main_domain': True
            })

        temp_conf_file = NamedTemporaryFile()
        temp_conf_file.write("[req]\n")
        temp_conf_file.write("prompt = no\n")
        temp_conf_file.write("default_bits = 2048\n")
        temp_conf_file.write("default_md = sha256\n")
        temp_conf_file.write("distinguished_name = dn\n")
        temp_conf_file.write("req_extensions = ext\n\n")
        temp_conf_file.write("[dn]\n")
        temp_conf_file.write("C = GB\n")
        temp_conf_file.write("CN = %s\n\n" % vhost.main_domain.name)
        temp_conf_file.write("[ext]\n")
        temp_conf_file.write("subjectAltName = DNS:" +
                             ", DNS:".join(set(vhost.domain_names.values_list('name', flat=True)) -
                                           set(vhost.main_domain.name)))
        temp_conf_file.flush()

        vhost.csr = subprocess.check_output(["openssl", "req", "-new", "-newkey", "rsa:2048", "-nodes", "-keyout",
                                             "/dev/null", "-config", temp_conf_file.name])
        vhost.save()

        temp_conf_file.close()
        # launch_ansible with a task to create the CSR
        # put the main domain name as the common name
        # include all domain names in the subject alternative name field in the extended configuration
        # country is always GB
        # all other parameters/fields are optional and won't appear in the certificate, just ignore them.

    return redirect(reverse(certificates, kwargs={'vhost_id': vhost.id}))


@login_required
def change_db_root_password(request, service_id):
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
                url=reverse(service_settings, kwargs={'service_id': service.id})),
        2: dict(name='Change db root pass', url=reverse(change_db_root_password, kwargs={'service_id': service.id})),
    }

    if request.method == 'POST':
        new_root_passwd = request.POST['new_root_passwd']
        # TODO implement
        return HttpResponseRedirect(reverse(service_settings, kwargs={'service_id': service.id}))

    return render(request, 'mws/change_db_root_password.html', {
        'breadcrumbs': breadcrumbs,
        'service': service,
        'site': site,
    })


@login_required
def backups(request, service_id):
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
                url=reverse(service_settings, kwargs={'service_id': service.id})),
        2: dict(name='Restore backup', url=reverse(backups, kwargs={'service_id': service.id})),
    }

    parameters = {
        'breadcrumbs': breadcrumbs,
        'service': service,
        'site': site,
        'fromdate': datetime.date.today()-datetime.timedelta(days=30),
        'todate': datetime.date.today()-datetime.timedelta(days=1),
    }

    if request.method == 'POST':
        try:
            backup_date = dateparse.parse_datetime(request.POST['backupdate'])
            if backup_date is None or backup_date > datetime.datetime.now() \
                    or backup_date < (datetime.datetime.now()-datetime.timedelta(days=30)):
                    # TODO or backup_date >= datetime.date.today() ????
                raise ValueError
            # TODO restore data, once successfully completed restore database data
            version = reversion.get_for_date(service, backup_date)
            version.revision.revert(delete=True)
            for domain in service.all_domain_names:
                if domain.status == "requested":
                    last_version = reversion.get_for_object(domain)[0]
                    if last_version.field_dict['id'] != domain.id:
                        raise Exception  # TODO change this to a custom exception
                    domain.status = last_version.field_dict['status']
                    domain.save()
        except ValueError:
            parameters['error_message'] = "Incorrect date"
            return render(request, 'mws/backups.html', parameters)
        except Exception as e:
            parameters['error_message'] = str(e)
            return render(request, 'mws/backups.html', parameters)

        # TODO do something + check that dates are correct
        return HttpResponseRedirect(reverse('sitesmanagement.views.show', kwargs={'site_id': site.id}))

    return render(request, 'mws/backups.html', parameters)
