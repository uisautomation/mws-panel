import mock
from datetime import datetime
from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from apimws.xen import new_site_primary_vm, change_vm_power_state, reset_vm, destroy_vm, clone_vm
from mwsauth.tests import do_test_login
from sitesmanagement.models import NetworkConfig, Site, Service, VirtualMachine


@override_settings(CELERY_EAGER_PROPAGATES_EXCEPTIONS=True, CELERY_ALWAYS_EAGER=True, BROKER_BACKEND='memory')
class XenAPITests(TestCase):
    def setUp(self):
        do_test_login(self, user="test0001")
        NetworkConfig.objects.create(IPv4='131.111.58.253', IPv6='2001:630:212:8::8c:253', type='ipvxpub',
                                     name="mws-66424.mws3.csx.cam.ac.uk")
        NetworkConfig.objects.create(IPv4='172.28.18.253', type='ipv4priv',
                                     name='mws-46250.mws3.csx.private.cam.ac.uk')
        NetworkConfig.objects.create(IPv6='2001:630:212:8::8c:ff4', name='mws-client1', type='ipv6')
        NetworkConfig.objects.create(IPv6='2001:630:212:8::8c:ff3', name='mws-client2', type='ipv6')
        NetworkConfig.objects.create(IPv6='2001:630:212:8::8c:ff2', name='mws-client3', type='ipv6')
        NetworkConfig.objects.create(IPv6='2001:630:212:8::8c:ff1', name='mws-client4', type='ipv6')

    def create_site_service(self):
        site = Site.objects.create(name="testSite", institution_id="testInst", start_date=datetime.today())
        site.users.add(User.objects.get(username='test0001'))
        service = Service.objects.create(site=site, type='production', status="ready",
                                         network_configuration=NetworkConfig.get_free_prod_service_config())
        service2 = Service.objects.create(site=site, type='test', status="ready",
                                          network_configuration=NetworkConfig.get_free_test_service_config())
        return service

    def test_create_api(self):
        with mock.patch("apimws.xen.VM_END_POINT_COMMAND", ["/Users/amc203/Development/python27dj17/bin/vmmanager"]):
            service = self.create_site_service()
            new_site_primary_vm(service)
            vm = VirtualMachine.objects.first()
            self.assertEqual(vm.service, service)
            change_vm_power_state(vm, "off")
            change_vm_power_state(vm, "on")
            reset_vm(vm)
            clone_vm(vm.site, vm)
            destroy_vm(vm)
