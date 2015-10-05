from datetime import datetime, date
import logging
from django.http import HttpResponse, HttpResponseNotFound
from django.views.decorators.csrf import csrf_exempt
import re
from stronghold.decorators import public
import subprocess
from apimws.models import AnsibleConfiguration
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
            if vm and (vm.network_configuration.IPv4 == ip or vm.network_configuration.IPv6 == ip):
                result = subprocess.check_output(["userv", "mws-admin", "mws_extract_lv_info",
                                                  vm.network_configuration.name])
                lvlist = []
                first_date = date.today()
                for lv in result.splitlines():
                    lv = lv.strip()
                    if re.search("^mws-snapshot-[0-9]{4}-[0-9]{2}-[0-9]{2}$", lv):
                        lvdate = datetime.strptime(lv.replace("mws-snapshot-", ""), '%Y-%m-%d').date()
                        if lvdate < first_date:
                            first_date = lvdate
                    elif re.search("^mws-snapshot-.+", lv):
                        lvlist.append(lv.replace("mws-snapshot-", ""))
                # Store the first date of an available backup in the database to be used by the front end
                backup_first_date = AnsibleConfiguration.objects.filter(service=vm.service, key="backup_first_date")
                if backup_first_date:
                    backup_first_date.value = first_date.isoformat()
                else:
                    AnsibleConfiguration.objects.create(service=vm.service, key="backup_first_date",
                                                        value=first_date.isoformat())
                # Delete entries in the DB related to backups no longer present on the client.
                for lv in vm.service.snapshots.all():
                    if lv.name not in lvlist:
                        lv.delete()
                LOGGER.info("VM %s LV list updated: %s" % (vm.name, lvlist))
                return HttpResponse(ip + ' %s' % vm.name)
    return HttpResponseNotFound()
