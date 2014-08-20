import csv
from datetime import date
import json
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, render, redirect
from stronghold.decorators import public
from mwsauth.utils import get_or_create_group_by_groupid
from sitesmanagement.models import VirtualMachine, DomainName, Site, EmailConfirmation
from apimws.models import VMForm
from sitesmanagement.views import show
from ucamlookup import user_in_groups


@login_required
def confirm_vm(request, vm_id):
    # Check if the request.user is authorised to do so: member of the UIS Platforms or UIS Information Systems groups
    if not user_in_groups(request.user,
                          [get_or_create_group_by_groupid(101128), get_or_create_group_by_groupid(101888)]):
        return HttpResponseForbidden()

    vm = get_object_or_404(VirtualMachine, pk=vm_id)

    if request.method == 'POST':
        vm_form = VMForm(request.POST, instance=vm)
        if vm_form.is_valid():
            vm = vm_form.save(commit=False)
            vm.status = "accepted"
            vm.save()
            return render(request, 'api/success.html')
    else:
        vm_form = VMForm(instance=vm)

    return render(request, 'api/confirm_vm.html', {
        'vm': vm,
        'vm_form': vm_form
    })


@login_required
def confirm_dns(request, dn_id):
    # Check if the request.user is authorised to do so: member of the UIS ip-register or UIS Information Systems groups
    # TODO change ip-register group == first groupid
    if not user_in_groups(request.user,
                          [get_or_create_group_by_groupid(101927), get_or_create_group_by_groupid(101888)]):
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
def billing_year(request, year):
    # Check if the request.user is authorised to do so: member of the uis-finance or UIS Information Systems groups
    if not user_in_groups(request.user,
                          [get_or_create_group_by_groupid(101923), get_or_create_group_by_groupid(101888)]):
        return HttpResponseForbidden()

    billing_list = map(lambda x: x.calculate_billing(financial_year_start=date(int(year), 8, 1),
                                                     financial_year_end=date(int(year)+1, 7, 31)),
                       Site.objects.all())
    billing_list = [x for x in billing_list if x is not None]

    # Create the HttpResponse object with the an excel header as a requirement of Finance
    response = HttpResponse(content_type='application/vnd.ms-excel')
    response['Content-Disposition'] = 'attachment; filename="mwsbilling%s.csv"' % year

    writer = csv.writer(response)
    for billing in billing_list:
        writer.writerow(billing)

    return response


@login_required
def confirm_email(request, ec_id, token):
    # TODO add a message to say that your email approval is pending
    # TODO add a message when doing the redirect to the site to inform the user that the email has been accepted
    email_confirmation = get_object_or_404(EmailConfirmation, pk=ec_id)

    # check that the token match

    if email_confirmation.token == token:
        email_confirmation.status = 'accepted'
        email_confirmation.save()
        return redirect(show, site_id=email_confirmation.site.id)
    else:
        raise Exception #TODO change this exception for an error message


@public
def dns_entries(request, token):
    # TODO test that the token matches the one we have stored
    json_object = {}
    json_object['protocol_version'] = 1
    json_object['mwsv3_sites'] = []
    for site in Site.objects.all():
        dns_entries = []
        primary_vm = site.primary_vm
        secondary_vm = site.secondary_vm
        if primary_vm:
            dns_entries.append({
                'name': primary_vm.network_configuration.mws_domain,
                'values': {
                    'A': primary_vm.network_configuration.IPv4,
                    'AAAA': primary_vm.network_configuration.IPv6
                },
            })
        if secondary_vm:
            dns_entries.append({
                'name': secondary_vm.network_configuration.mws_domain,
                'values': {
                    'A': secondary_vm.network_configuration.IPv4,
                    'AAAA': secondary_vm.network_configuration.IPv6,
                    'SSHFP': secondary_vm.network_configuration.SSHFP
                },
            })
        for dn in site.domain_names.all():
            dns_entries.append({
                'name': dn.name,
                'values': {
                    'CNAME': primary_vm.network_configuration.mws_domain
                },
            })
        if dns_entries:
            json_object['mwsv3_sites'].append({
                'mwsv3_name': site.name,
                'changed': len(site.domain_names.filter(status='requested')) > 0,
                'dns_entries': dns_entries,
            })
    return HttpResponse(json.dumps(json_object, indent=4), content_type='application/json')