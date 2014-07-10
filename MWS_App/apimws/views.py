import json
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from sitesmanagement.models import VirtualMachine, DomainName
from apimws.models import VMForm
from apimws.utils import get_users_from_query, get_groups_from_query


@login_required()
def confirm_vm(request, vm_id):
    vm = get_object_or_404(VirtualMachine, pk=vm_id)

    # check if the request.user is authorised to do so: member of the UIS Platforms or UIS Information Systems groups

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


@login_required()
def confirm_dns(request, dn_id):
    dn = get_object_or_404(DomainName, pk=dn_id)

    # check if the request.user is authorised to do so: member of the UIS ip-register or UIS Information Systems groups

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


@login_required()
def find_people(request):
    persons = get_users_from_query(request.GET.get('query'))
    return HttpResponse(json.dumps({'searchId_u': request.GET.get('searchId_u'), 'persons': persons}),
                        content_type='application/json')


@login_required()
def find_groups(request):
    groups = get_groups_from_query(request.GET.get('query'))
    return HttpResponse(json.dumps({'searchId_g': request.GET.get('searchId_g'), 'groups': groups}),
                        content_type='application/json')