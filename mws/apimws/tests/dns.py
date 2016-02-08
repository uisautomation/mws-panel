import mock
from django.core.urlresolvers import reverse
from django.test import override_settings, TestCase

from mwsauth.tests import do_test_login
from sitesmanagement.models import Vhost, DomainName
from sitesmanagement.tests.tests import assign_a_site


@override_settings(CELERY_EAGER_PROPAGATES_EXCEPTIONS=True, CELERY_ALWAYS_EAGER=True, BROKER_BACKEND='memory')
class DNSTests(TestCase):
    def setUp(self):
        do_test_login(self, user="test0001")
        assign_a_site(self)

    def test_add_external_domain(self):
        vhost = Vhost.objects.first()
        test_external_domain = 'externaldomain.com'
        with mock.patch("apimws.ansible.subprocess") as mock_subprocess:
            mock_subprocess.check_output.return_value.returncode = 0
            self.client.post(reverse('sitesmanagement.views.add_domain', kwargs={'vhost_id': vhost.id}),
                             {'name': test_external_domain})
        domain_name_created = DomainName.objects.first()
        self.assertEquals(domain_name_created.name, test_external_domain)
        self.assertEquals(domain_name_created.status, 'external')
        self.assertEquals(domain_name_created.vhost, vhost)
        self.assertEquals(domain_name_created.requested_by.username, "test0001")
        self.assertIsNone(domain_name_created.reject_reason)
        self.assertIsNotNone(domain_name_created.token)
        self.assertIsNone(domain_name_created.authorised_by)
