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

    @override_settings(VM_END_POINT_COMMAND=["vmmanager"])
    def test_xen_api(self):
        # We get a free service address
        service = self.create_site_service()
        # Xen API create call with the free service address previously retrieved
        new_site_primary_vm(service)
        # We retrieve the VM created by the create Xen API call
        vm = VirtualMachine.objects.first()
        self.assertEqual(vm.service, service)
        # We try that the switch off change of state works
        change_vm_power_state(vm, "off")
        # We try that the switch on change of state works
        change_vm_power_state(vm, "on")
        # We try that the reset call works
        reset_vm(vm)
        # We clone the production VM to a test VM
        site = vm.site
        clone_vm(site, vm)
        # We try the deletion of both VMs through a Xen API call
        destroy_vm(site.secondary_vm)
        destroy_vm(site.primary_vm)
