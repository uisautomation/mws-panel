from django.test import override_settings, TestCase
from mwsauth.tests import do_test_login
from sitesmanagement.models import Vhost
from sitesmanagement.tests.tests import assign_a_site


@override_settings(CELERY_EAGER_PROPAGATES_EXCEPTIONS=True, CELERY_ALWAYS_EAGER=True, BROKER_BACKEND='memory')
class VhostTests(TestCase):
    def setUp(self):
        do_test_login(self, user="test0001")
        assign_a_site(self)

    def test_default_vhost_created(self):
        self.assertEquals(Vhost.objects.count(), 1)
        default_vhost = Vhost.objects.first()
        self.assertEquals(default_vhost.name, 'default')
        self.assertIsNone(default_vhost.main_domain)
        self.assertIsNotNone(default_vhost.service)
        self.assertIsNone(default_vhost.csr)
        self.assertIsNone(default_vhost.certificate)
        self.assertIsNone(default_vhost.tls_key_hash)
        self.assertFalse(default_vhost.tls_enabled)
        self.assertIsNone(default_vhost.webapp)
