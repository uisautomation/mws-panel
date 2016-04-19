import mock
from django.test import TestCase, override_settings
from apimws.xen import change_vm_power_state, reset_vm, destroy_vm, clone_vm_api_call
from mwsauth.tests import do_test_login
from sitesmanagement.models import VirtualMachine
from sitesmanagement.tests.tests import assign_a_site


@override_settings(CELERY_EAGER_PROPAGATES_EXCEPTIONS=True, CELERY_ALWAYS_EAGER=True, BROKER_BACKEND='memory')
class XenAPITests(TestCase):
    def setUp(self):
        do_test_login(self, "test0001")
        assign_a_site(self)

    def test_xen_api(self):
        # We retrieve the VM created by the create Xen API call
        vm = VirtualMachine.objects.first()
        with mock.patch("apimws.xen.app") as mock_xen_app:
            mock_xen_app.control.inspect.active.values.return_value = []
            with mock.patch("apimws.xen.vm_api_request") as mock_vm_api_request:
                mock_vm_api_request.return_value = "{}"
                # We try that the switch off change of state works
                change_vm_power_state(vm.id, "off")
                # We try that the switch on change of state works
                change_vm_power_state(vm.id, "on")
                # We try that the reset call works
                reset_vm(vm.id)
                # We clone the production VM to a test VM
                site = vm.site
                clone_vm_api_call(site)
                # We try the deletion of both VMs through a Xen API call
                destroy_vm(site.secondary_vm.id)
                destroy_vm(site.primary_vm.id)
