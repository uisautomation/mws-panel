import os
from django.conf import settings
from django.core.urlresolvers import reverse
from django.test import override_settings, TestCase
from mwsauth.tests import do_test_login
from sitesmanagement.models import Vhost, DomainName
from sitesmanagement.tests.tests import assign_a_site


@override_settings(CELERY_EAGER_PROPAGATES_EXCEPTIONS=True, CELERY_ALWAYS_EAGER=True, BROKER_BACKEND='memory')
class VhostTests(TestCase):
    fixtures = [os.path.join(settings.BASE_DIR, 'sitesmanagement/fixtures/amc203_test_IPs.yaml'), ]
    def setUp(self):
        do_test_login(self, user="test0001")
        assign_a_site(self)

    def test_default_vhost_created(self):
        self.assertEquals(Vhost.objects.count(), 2)
        self.assertEquals(DomainName.objects.count(), 2)
        default_vhost = Vhost.objects.first()
        self.assertEquals(default_vhost.name, 'default')
        self.assertEqual(default_vhost.main_domain,
                         DomainName.objects.get(name=default_vhost.service.network_configuration.name))
        self.assertIsNotNone(default_vhost.service)
        self.assertIsNone(default_vhost.csr)
        self.assertIsNone(default_vhost.certificate)
        self.assertIsNone(default_vhost.tls_key_hash)
        self.assertFalse(default_vhost.tls_enabled)
        self.assertIsNone(default_vhost.webapp)

    def test_default_vhost_and_dn_cannot_be_deleted(self):
        vhost = Vhost.objects.last()
        response = self.client.post(reverse('deletevhost', kwargs={'vhost_id': vhost.id}))
        self.assertEqual(response.status_code, 403)
        self.assertEquals(Vhost.objects.count(), 2)

        dn = DomainName.objects.first()
        response = self.client.post(reverse('deletedomain', kwargs={'domain_id': dn.id}))
        self.assertEqual(response.status_code, 403)
        self.assertEquals(DomainName.objects.count(), 2)
