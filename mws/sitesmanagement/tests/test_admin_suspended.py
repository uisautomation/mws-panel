import os
from django.conf import settings
from django.core.urlresolvers import reverse
from django.test import override_settings, TestCase
from mock import mock
from mwsauth.tests import do_test_login
from sitesmanagement.models import Site
from sitesmanagement.tests.tests import assign_a_site


@override_settings(CELERY_EAGER_PROPAGATES_EXCEPTIONS=True, CELERY_ALWAYS_EAGER=True, BROKER_BACKEND='memory')
class AdminSuspendedTests(TestCase):
    fixtures = [os.path.join(settings.BASE_DIR, 'sitesmanagement/fixtures/network_configuration_dev.yaml'), ]
    def setUp(self):
        do_test_login(self, user="test0001")
        assign_a_site(self)

    def test_user_has_no_access_admin_suspended_disabled_site(self):
        site = Site.objects.last()
        site.suspend_now("Test Admin suspended")

        with mock.patch("apimws.vm.change_vm_power_state") as mock_change_vm_power_state:
            mock_change_vm_power_state.return_value = True
            mock_change_vm_power_state.delay.return_value = True
            site.disable()

        self.assertTrue(site.disabled)
        self.assertTrue(site.is_admin_suspended())

        response = self.client.get(reverse('listsites'))
        self.assertContains(response, "Disabled MWS servers where you are the administrator")
        self.assertContains(response, "This server has been administratively suspended")
        self.assertTrue(site.is_admin_suspended())
