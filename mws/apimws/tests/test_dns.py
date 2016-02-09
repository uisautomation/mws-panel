import mock
from django.core import mail
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

    def test_add_internal_mws3_domain(self):
        vhost = Vhost.objects.first()
        test_internal_mws3_domain = 'test.usertest.mws3.csx.cam.ac.uk'
        with mock.patch("apimws.ansible.subprocess") as mock_subprocess:
            mock_subprocess.check_output.return_value.returncode = 0
            with mock.patch("sitesmanagement.views.domains.set_cname") as mock_set_cname:
                mock_set_cname.return_value = True
                self.client.post(reverse('sitesmanagement.views.add_domain', kwargs={'vhost_id': vhost.id}),
                                 {'name': test_internal_mws3_domain})
        domain_name_created = DomainName.objects.first()
        self.assertEquals(domain_name_created.name, test_internal_mws3_domain)
        self.assertEquals(domain_name_created.status, 'accepted')
        self.assertEquals(domain_name_created.vhost, vhost)
        self.assertEquals(domain_name_created.requested_by.username, "test0001")
        self.assertIsNone(domain_name_created.reject_reason)
        self.assertIsNotNone(domain_name_created.token)
        self.assertIsNone(domain_name_created.authorised_by)

    def add_internal_non_existing_cam_domain(self):
        vhost = Vhost.objects.first()
        test_internal_cam_domain = 'domaintest.cam.ac.uk'
        test_email = 'amc203@cam.ac.uk'
        with mock.patch("apimws.ansible.subprocess") as mock_subprocess:
            mock_subprocess.check_output.return_value.returncode = 0
            with mock.patch("apimws.utils.get_nameinfo") as mock_get_nameinfo:
                mock_get_nameinfo.return_value = {'emails': [test_email], 'domain': test_internal_cam_domain, 'exists':
                                                  []}
                self.client.post(reverse('sitesmanagement.views.add_domain', kwargs={'vhost_id': vhost.id}),
                                 {'name': test_internal_cam_domain})
        self.assertEqual(len(mail.outbox), 2)  # The first email is the one asking to confirm user's email
        # generated during the setup of this test
        self.assertEqual(mail.outbox[1].subject,
                         "Domain name authorisation request for %s" % test_internal_cam_domain)
        self.assertEqual(mail.outbox[1].to, [test_email])
        domain_name_created = DomainName.objects.first()
        self.assertEquals(domain_name_created.name, test_internal_cam_domain)
        self.assertEquals(domain_name_created.status, 'requested')
        self.assertEquals(domain_name_created.vhost, vhost)
        self.assertEquals(domain_name_created.requested_by.username, "test0001")
        self.assertIsNone(domain_name_created.reject_reason)
        self.assertIsNotNone(domain_name_created.token)
        self.assertIsNone(domain_name_created.authorised_by)
        return domain_name_created

    def test_add_internal_acceptable_non_existing_cam_domain(self):
        domain_name_created = self.add_internal_non_existing_cam_domain()
        with mock.patch("apimws.views.get_nameinfo") as mock_get_nameinfo:
            # First test a non changeable domain name, one that does not exists
            mock_get_nameinfo.return_value = {'exists': ['V']}
            self.client.post(reverse('apimws.views.confirm_dns',
                                     kwargs={'dn_id': domain_name_created.id, 'token': domain_name_created.token}),
                             {'accepted': '1'})
        # Check that it hasn't been accepted because the domain name is unchangeable
        # (it does not exists or it is a CNAME)
        domain_name_created = DomainName.objects.get(id=domain_name_created.id)  # Refresh object from DB
        self.assertEquals(domain_name_created.status, 'requested')
        with mock.patch("apimws.views.get_nameinfo") as mock_get_nameinfo:
            # Now test accept a changeable domain name
            mock_get_nameinfo.return_value = {'exists': ['C']}
            with mock.patch("apimws.views.set_cname") as mock_set_cname:
                mock_set_cname.return_value = True
                self.client.post(reverse('apimws.views.confirm_dns',
                                         kwargs={'dn_id': domain_name_created.id, 'token': domain_name_created.token}),
                                 {'accepted': '1'})
        domain_name_created = DomainName.objects.get(id=domain_name_created.id)  # Refresh object from DB
        self.assertEquals(domain_name_created.status, 'accepted')
        self.assertEquals(domain_name_created.authorised_by.username, 'test0001')


    def test_add_internal_rejectable_non_existing_cam_domain(self):
        domain_name_created = self.add_internal_non_existing_cam_domain()
        with mock.patch("apimws.views.get_nameinfo") as mock_get_nameinfo:
            # First test a non changeable domain name, one that does not exists
            mock_get_nameinfo.return_value = {'exists': []}
            self.client.post(reverse('apimws.views.confirm_dns',
                                     kwargs={'dn_id': domain_name_created.id, 'token': domain_name_created.token}),
                             {'accepted': '0'})
        domain_name_created = DomainName.objects.get(id=domain_name_created.id)  # Refresh object from DB
        # Check that it has been rejected
        self.assertEquals(domain_name_created.status, 'denied')
