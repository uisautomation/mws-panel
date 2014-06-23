from django.shortcuts import get_object_or_404, render
from SitesManagement.models import Site, NetworkConfig
from apimws.models import VMForm


def confirm_vm(request, site_id, network_conf_id, primary_or_secondary):
    site = get_object_or_404(Site, pk=site_id)
    network_conf = get_object_or_404(NetworkConfig, pk=network_conf_id)

    # check if the request.user is authorised to do so: member of the UIS Platforms or UIS Information Systems groups

    if primary_or_secondary == 'primary':
        primary = True
    elif primary_or_secondary == 'secondary':
        primary = False

    if request.method == 'POST':
        if site.vm(primary=primary):
            vm_form = VMForm(request.POST, instance=site.vm(primary=primary))
            if vm_form.is_valid():
                vm_form.save()
                return render(request, 'api/success.html')
        else:
            vm_form = VMForm(request.POST)
            if vm_form.is_valid():
                vm = vm_form.save(commit=False)
                vm.primary = primary
                vm.site = site
                vm.network_configuration = network_conf
                vm.save()
                return render(request, 'api/success.html')
    else:
        if not site.vm(primary=primary):
            vm_form = VMForm()
        else:
            vm_form = VMForm(instance=site.vm(primary=primary))

    return render(request, 'api/confirm_vm.html', {
        'site': site,
        'vm_form': vm_form,
        'primary_or_secondary': primary_or_secondary,
        'network_conf': network_conf
    })