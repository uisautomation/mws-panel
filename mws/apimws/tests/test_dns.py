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
            mock_subprocess.check_output.assert_called_once_with(["userv", "mws-admin", "mws_ansible_host",
                                                                  vhost.service.virtual_machines.first()
                                                                 .network_configuration.name],
                                                                 stderr=mock_subprocess.STDOUT)
        domain_name_created = DomainName.objects.last()
        self.assertEquals(domain_name_created.name, test_external_domain)
        self.assertEquals(domain_name_created.status, 'external')
        self.assertEquals(domain_name_created.vhost, vhost)
        self.assertEquals(domain_name_created.requested_by.username, "test0001")
        self.assertIsNone(domain_name_created.reject_reason)
        self.assertIsNotNone(domain_name_created.token)
        self.assertIsNone(domain_name_created.authorised_by)

    def test_add_internal_mws3_domain(self):
        vhost = Vhost.objects.first()
        test_internal_mws3_domain = 'test.mws3.csx.cam.ac.uk'
        with mock.patch("apimws.ansible.subprocess") as mock_subprocess:
            mock_subprocess.check_output.return_value.returncode = 0
            with mock.patch("sitesmanagement.views.domains.set_cname") as mock_set_cname:
                mock_set_cname.return_value = True
                self.client.post(reverse('sitesmanagement.views.add_domain', kwargs={'vhost_id': vhost.id}),
                                 {'name': test_internal_mws3_domain})
                mock_subprocess.check_output.assert_called_once_with(["userv", "mws-admin", "mws_ansible_host",
                                                                      vhost.service.virtual_machines.first()
                                                                     .network_configuration.name],
                                                                     stderr=mock_subprocess.STDOUT)
                mock_set_cname.check_output.assert_not_called()
        domain_name_created = DomainName.objects.last()
        self.assertEquals(domain_name_created.name, test_internal_mws3_domain)
        self.assertEquals(domain_name_created.status, 'denied')
        self.assertEquals(domain_name_created.vhost, vhost)
        self.assertEquals(domain_name_created.requested_by.username, "test0001")
        self.assertIsNone(domain_name_created.reject_reason)
        self.assertIsNotNone(domain_name_created.token)
        self.assertIsNone(domain_name_created.authorised_by)

    def test_add_internal_usertest_mws3_domain(self):
        vhost = Vhost.objects.first()
        test_internal_mws3_domain = 'test.usertest.mws3.csx.cam.ac.uk'
        with mock.patch("apimws.ansible.subprocess") as mock_subprocess:
            mock_subprocess.check_output.return_value.returncode = 0
            with mock.patch("sitesmanagement.views.domains.set_cname") as mock_set_cname:
                mock_set_cname.return_value = True
                self.client.post(reverse('sitesmanagement.views.add_domain', kwargs={'vhost_id': vhost.id}),
                                 {'name': test_internal_mws3_domain})
                mock_subprocess.check_output.assert_called_once_with(["userv", "mws-admin", "mws_ansible_host",
                                                                      vhost.service.virtual_machines.first()
                                                                     .network_configuration.name],
                                                                     stderr=mock_subprocess.STDOUT)
                mock_set_cname.check_output.assert_not_called()
        domain_name_created = DomainName.objects.last()
        self.assertEquals(domain_name_created.name, test_internal_mws3_domain)
        self.assertEquals(domain_name_created.status, 'accepted')
        self.assertEquals(domain_name_created.vhost, vhost)
        self.assertEquals(domain_name_created.requested_by.username, "test0001")
        self.assertIsNone(domain_name_created.reject_reason)
        self.assertIsNotNone(domain_name_created.token)
        self.assertIsNone(domain_name_created.authorised_by)

    def test_duplicate_domain(self):
        self.test_add_internal_usertest_mws3_domain()
        vhost = Vhost.objects.first()
        num_domains = DomainName.objects.count()
        test_duplicate_domain = 'test.usertest.mws3.csx.cam.ac.uk'
        with mock.patch("apimws.ansible.subprocess") as mock_subprocess:
            mock_subprocess.check_output.return_value.returncode = 0
            with mock.patch("sitesmanagement.views.domains.set_cname") as mock_set_cname:
                mock_set_cname.return_value = True
                response = self.client.post(reverse('sitesmanagement.views.add_domain', kwargs={'vhost_id': vhost.id}),
                                            {'name': test_duplicate_domain})
                mock_subprocess.check_output.assert_not_called()
                mock_set_cname.check_output.assert_not_called()
        self.assertEqual(num_domains, DomainName.objects.count())
        self.assertContains(response, "Domain name with this Name already exists.")

    def add_internal_non_existing_cam_domain(self):
        vhost = Vhost.objects.first()
        test_internal_cam_domain = 'domaintest.cam.ac.uk'
        test_email = 'amc203@cam.ac.uk'
        with mock.patch("apimws.ansible.subprocess") as mock_subprocess:
            mock_subprocess.check_output.return_value.returncode = 0
            with mock.patch("apimws.ipreg.get_nameinfo") as mock_get_nameinfo:
                mock_get_nameinfo.return_value = {'emails': [test_email], 'domain': test_internal_cam_domain, 'exists':
                                                  []}
                self.client.post(reverse('sitesmanagement.views.add_domain', kwargs={'vhost_id': vhost.id}),
                                 {'name': test_internal_cam_domain})
        self.assertEqual(len(mail.outbox), 2)  # The first email is the one asking to confirm user's email
        # generated during the setup of this test
        self.assertEqual(mail.outbox[1].subject,
                         "Domain name authorisation request for %s" % test_internal_cam_domain)
        self.assertEqual(mail.outbox[1].to, [test_email])
        domain_name_created = DomainName.objects.last()
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
            with mock.patch("apimws.ipreg.set_cname") as mock_set_cname:
                mock_set_cname.return_value = True
                with mock.patch("apimws.ansible.subprocess") as mock_subprocess:
                    mock_subprocess.check_output.return_value.returncode = 0
                    self.client.post(reverse('apimws.views.confirm_dns',
                                             kwargs={'dn_id': domain_name_created.id,
                                                     'token': domain_name_created.token}), {'accepted': '1'})
                    mock_subprocess.check_output.assert_called_once_with(["userv", "mws-admin", "mws_ansible_host",
                                                      Vhost.objects.first().service.virtual_machines.first()
                                                     .network_configuration.name],
                                                     stderr=mock_subprocess.STDOUT)
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

    def test_deletion_accepted_domain(self):
        test_internal_mws3_domain = 'test.usertest.mws3.csx.cam.ac.uk'
        dn = DomainName.objects.create(name=test_internal_mws3_domain, status="accepted", vhost=Vhost.objects.first())
        # Get should not work
        self.client.get(reverse('deletedomain', kwargs={'domain_id': dn.id}))
        DomainName.objects.get(pk=dn.pk)
        # Test deletion of accepted domain
        with mock.patch("apimws.ansible.subprocess") as mock_subprocess:
            mock_subprocess.check_output.return_value.returncode = 0
            with mock.patch("apimws.ipreg.ip_reg_call") as mock_ip_reg_call:
                mock_ip_reg_call.return_value = {}
                self.client.post(reverse('deletedomain', kwargs={'domain_id': dn.id}))
                mock_ip_reg_call.assert_called_once_with(['delete', 'cname', test_internal_mws3_domain])
            mock_subprocess.check_output.assert_called_once_with(["userv", "mws-admin", "mws_ansible_host",
                                                                  Vhost.objects.first().service.virtual_machines.first()
                                                                 .network_configuration.name],
                                                                 stderr=mock_subprocess.STDOUT)
        with self.assertRaises(DomainName.DoesNotExist):
            DomainName.objects.get(pk=dn.pk)

    def test_deletion_external_domain(self):
        test_external_domain = 'externaldomain.com'
        dn = DomainName.objects.create(name=test_external_domain, status="external", vhost=Vhost.objects.first())
        # Get should not work
        self.client.get(reverse('deletedomain', kwargs={'domain_id': dn.id}))
        DomainName.objects.get(pk=dn.pk)
        # Test deletion of external domain
        with mock.patch("apimws.ansible.subprocess") as mock_subprocess:
            mock_subprocess.check_output.return_value.returncode = 0
            with mock.patch("apimws.ipreg.ip_reg_call") as mock_ip_reg_call:
                mock_ip_reg_call.return_value = {}
                self.client.post(reverse('deletedomain', kwargs={'domain_id': dn.id}))
                assert not mock_ip_reg_call.called
            mock_subprocess.check_output.assert_called_once_with(["userv", "mws-admin", "mws_ansible_host",
                                                                  Vhost.objects.first().service.virtual_machines.first()
                                                                 .network_configuration.name],
                                                                 stderr=mock_subprocess.STDOUT)
        with self.assertRaises(DomainName.DoesNotExist):
            DomainName.objects.get(pk=dn.pk)

    def test_deletion_requested_domain(self):
        test_internal_mws3_domain = 'test.usertest.mws3.csx.cam.ac.uk'
        dn = DomainName.objects.create(name=test_internal_mws3_domain, status="requested", vhost=Vhost.objects.first())
        # Get should not work
        self.client.get(reverse('deletedomain', kwargs={'domain_id': dn.id}))
        DomainName.objects.get(pk=dn.pk)
        # Test deletion of requested domain
        with mock.patch("apimws.ansible.subprocess") as mock_subprocess:
            mock_subprocess.check_output.return_value.returncode = 0
            with mock.patch("apimws.ipreg.ip_reg_call") as mock_ip_reg_call:
                mock_ip_reg_call.return_value = {}
                self.client.post(reverse('deletedomain', kwargs={'domain_id': dn.id}))
                assert not mock_ip_reg_call.called
            mock_subprocess.check_output.assert_called_once_with(["userv", "mws-admin", "mws_ansible_host",
                                                                  Vhost.objects.first().service.virtual_machines.first()
                                                                 .network_configuration.name],
                                                                 stderr=mock_subprocess.STDOUT)
        with self.assertRaises(DomainName.DoesNotExist):
            DomainName.objects.get(pk=dn.pk)
