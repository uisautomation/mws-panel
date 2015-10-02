import logging
from django.http import HttpResponse, HttpResponseNotFound
from django.views.decorators.csrf import csrf_exempt
from stronghold.decorators import public
from sitesmanagement.models import VirtualMachine
from sitesmanagement.utils import get_object_or_None


LOGGER = logging.getLogger('mws')


@public
@csrf_exempt
def update_lv_list(request):
    if request.method == 'POST':
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        LOGGER.info("Machine with IP %s poked the web panel interface to update a VM's LV list" % ip)
        if 'hostname' in request.POST:
            vm = get_object_or_None(VirtualMachine, name=request.POST['hostname'])
            if vm and (vm.network_configuration.IPv4==ip or vm.network_configuration.IPv6==ip):
                LOGGER.info("VM %s LV list updated" % vm.name)
                return HttpResponse(ip + ' %s' % vm.name)
    return HttpResponseNotFound()
