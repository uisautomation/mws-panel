import csv
from datetime import date
import json
import logging
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, render, redirect
from django.views.decorators.csrf import csrf_exempt
from stronghold.decorators import public
from apimws.ansible import launch_ansible_async
from mwsauth.utils import get_or_create_group_by_groupid, privileges_check
from sitesmanagement.models import DomainName, Site, EmailConfirmation, VirtualMachine, Billing
from ucamlookup import user_in_groups


logger = logging.getLogger('mws')


@login_required
def confirm_dns(request, dn_id):
    # Check if the request.user is authorised to do so: member of the UIS ip-register or UIS Information Systems groups
    # TODO change ip-register group == first groupid
    if not user_in_groups(request.user,
                          [get_or_create_group_by_groupid("101927"), get_or_create_group_by_groupid("101888")]):
        return HttpResponseForbidden()

    dn = get_object_or_404(DomainName, pk=dn_id)

    if request.method == 'POST':
        if request.POST.get('accepted') == '1':
            dn.status = 'accepted'
        else:
            dn.status = 'denied'
        dn.save()
        return render(request, 'api/success.html')

    return render(request, 'api/confirm_dns.html', {
        'dn': dn,
    })


@login_required
def billing_total(request):
    # Check if the request.user is authorised to do so: member of the uis-finance or UIS Information Systems groups
    if not user_in_groups(request.user,
                          [get_or_create_group_by_groupid("101923"), get_or_create_group_by_groupid("101888")]):
        return HttpResponseForbidden()

    return render(request, 'api/finance_total.html', {
        'billings': Billing.objects.filter(site__deleted=False),
        'year_cost': settings.YEAR_COST,
    })


@login_required
def billing_month(request, year, month):
    # Check if the request.user is authorised to do so: member of the uis-finance or UIS Information Systems groups
    if not user_in_groups(request.user,
                          [get_or_create_group_by_groupid("101923"), get_or_create_group_by_groupid("101888")]):
        return HttpResponseForbidden()

    month = int(month)
    year = int(year)

    if not (1 <= month <= 12):
        return HttpResponseForbidden()

    if month == 1:
        inidate = date(year-1, 12, 1)
    else:
        inidate = date(year, month-1, 1)

    return render(request, 'api/finance_month.html', {
        'new_sites_billing': Billing.objects.filter(site__start_date__month=inidate.month,
                                                    site__start_date__year=inidate.year, site__deleted=False),
        'renewal_sites_billing': Billing.objects.filter(site__start_date__month=month,
                                                        site__start_date__lt=date(year, 1, 1), site__deleted=False),
        'year': year,
        'month': month,
        'year_cost': settings.YEAR_COST,
    })

@login_required
def confirm_email(request, ec_id, token):
    # TODO add a message to say that your email approval is pending
    # TODO add a message when doing the redirect to the site to inform the user that the email has been accepted
    email_confirmation = get_object_or_404(EmailConfirmation, pk=ec_id)

    # check that the token match

    if email_confirmation.token == token:
        email_confirmation.status = 'accepted'
        email_confirmation.save()
        logger.info(str(request.user.username) + " confirmed email '" + str(email_confirmation.email) + "'")
        # launch_ansible_site(email_confirmation.site)  # to update server email associated
        return redirect(email_confirmation.site)
    else:
        raise Exception  # TODO change this exception for an error message


@public
def dns_entries(request, token):
    # TODO test that the token matches the one we have stored
    json_object = {
        'mwsv3_sites': [],
    }
    for site in Site.objects.all():
        primary_vm = site.primary_vm
        secondary_vm = site.secondary_vm
        if primary_vm and primary_vm.ip_register_domains:
            dns_entries = []
            for domain in primary_vm.ip_register_domains:
                dns_entries.append({"domain": domain.name})
            json_object['mwsv3_sites'].append({
                'hostname': primary_vm.site.service_network_configuration.mws_domain,
                'aliases': dns_entries
            })
        if secondary_vm and secondary_vm.ip_register_domains:
            dns_entries = []
            for domain in secondary_vm.ip_register_domains:
                dns_entries.append({"domain": domain.name})
            json_object['mwsv3_sites'].append({
                'hostname': secondary_vm.site.service_network_configuration.mws_domain,
                'aliases': dns_entries
            })
    aliases_to_be_deleted = []
    for domain in DomainName.objects.filter(status='to_be_deleted'):
        aliases_to_be_deleted.append({
            'domain': domain.name
        })
    if aliases_to_be_deleted:
        json_object['aliases_to_be_deleted'] = aliases_to_be_deleted
    return HttpResponse(json.dumps(json_object, indent=4), content_type='application/json')

    headers = {'Content-type': 'application/json'}
    r = requests.post("somewhere/vm.json", data=json.dumps(json_object), headers=headers)
    response = json.loads(r.text)
    if response['success']:
        return True  # Success
    else:
        return False  # TODO Read errors

    # TODO check aliases_deleted


@public
@csrf_exempt
def post_installation(request):
    if request.method == 'POST':
        vm_id = request.POST['vm']
        token = request.POST['token']
        if not vm_id or not token:
            return HttpResponseForbidden()

        vm = VirtualMachine.objects.get(id=vm_id)

        if vm.token == token:
            service = vm.service
            if service.status != "installing":
                raise Exception("The service wasn't in the OS installation process")  # TODO raise custom exception
            service.status = 'ansible'
            service.save()
            launch_ansible_async.apply_async((service, ), countdown=90)
            # Wait 90 seconds before launching ansible, this will allow the machine have time to complete the reboot
            from apimws.utils import finished_installation_email_confirmation
            finished_installation_email_confirmation.delay(service.site)  # Perhaps after ansible has finished?
            return HttpResponse()

    return HttpResponseForbidden()


@login_required
def resend_email_confirmation_view(request, site_id):
    site = privileges_check(site_id, request.user)

    if site is None:
        return HttpResponseForbidden()

    if request.method == 'POST':
        from apimws.utils import send_email_confirmation
        send_email_confirmation.delay(site)
    else:
        return HttpResponseForbidden()

    return HttpResponse()
