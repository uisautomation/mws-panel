from django.shortcuts import get_object_or_404, render
from SitesManagement.models import VirtualMachine
from apimws.models import VMForm


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