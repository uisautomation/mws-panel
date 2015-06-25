import uuid
import mock
import os
import reversion
from datetime import datetime
from django.conf import settings
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test import TestCase, override_settings
from apimws.models import AnsibleConfiguration
from apimws.views import post_installation
from mwsauth.tests import do_test_login
import sitesmanagement.views as views
from sitesmanagement.models import Site, VirtualMachine, UnixGroup, Vhost, DomainName, NetworkConfig, Service
from sitesmanagement.utils import is_camacuk, get_object_or_None


@override_settings(CELERY_EAGER_PROPAGATES_EXCEPTIONS=True, CELERY_ALWAYS_EAGER=True, BROKER_BACKEND='memory')
class SiteManagementTests(TestCase):

    def create_site(self):
        NetworkConfig.objects.create(IPv4='131.111.58.253', IPv6='2001:630:212:8::8c:253', type='ipvxpub',
                                     name="mws-66424.mws3.csx.cam.ac.uk")

        NetworkConfig.objects.create(IPv4='172.28.18.253', type='ipv4priv',
                                     name='mws-46250.mws3.csx.private.cam.ac.uk')

        NetworkConfig.objects.create(IPv6='2001:630:212:8::8c:ff4', name='mws-client1', type='ipv6')
        NetworkConfig.objects.create(IPv6='2001:630:212:8::8c:ff3', name='mws-client2', type='ipv6')
        NetworkConfig.objects.create(IPv6='2001:630:212:8::8c:ff2', name='mws-client3', type='ipv6')
        NetworkConfig.objects.create(IPv6='2001:630:212:8::8c:ff1', name='mws-client4', type='ipv6')

        site = Site.objects.create(name="testSite", institution_id="testInst", start_date=datetime.today())
        site.users.add(User.objects.get(username='test0001'))
        service = Service.objects.create(site=site, type='production', status="ready",
                                         network_configuration=NetworkConfig.get_free_prod_service_config())
        VirtualMachine.objects.create(name="test_vm", token=uuid.uuid4(),
                                      service=service, network_configuration=NetworkConfig.get_free_host_config())

        return site

    def test_is_camacuk_helper(self):
        self.assertTrue(is_camacuk("www.cam.ac.uk"))
        self.assertFalse(is_camacuk("www.com.ac.uk"))

    def test_get_object_or_none(self):
        self.assertIsNone(get_object_or_None(User, username="test0001"))
        User.objects.create_user(username="test0001")
        self.assertIsNotNone(get_object_or_None(User, username="test0001"))

    def test_view_index(self):
        response = self.client.get(reverse('listsites'))
        self.assertEqual(response.status_code, 302)  # Not logged in, redirected to login
        self.assertTrue(response.url.endswith(
            '%s?next=%s' % (reverse('raven_login'), reverse('listsites'))))

        do_test_login(self, user="test0001")

        response = self.client.get(reverse('listsites'))
        self.assertInHTML("<p class=\"campl-notifications-icon campl-warning-icon\" style=\"float:none; margin-bottom: "
                          "10px;\">At this moment we cannot process any new request for the Managed Web Service, please"
                          " try again later.</p>", response.content)

        NetworkConfig.objects.create(IPv4='131.111.58.253', IPv6='2001:630:212:8::8c:253', type='ipvxpub',
                                     name="mws-66424.mws3.csx.cam.ac.uk")

        NetworkConfig.objects.create(IPv4='172.28.18.253', type='ipv4priv',
                                     name='mws-46250.mws3.csx.private.cam.ac.uk')

        NetworkConfig.objects.create(IPv6='2001:630:212:8::8c:ff4', name='mws-client1', type='ipv6')

        response = self.client.get(reverse('listsites'))
        self.assertInHTML("<p><a href=\"%s\" class=\"campl-primary-cta\">Register new server</a></p>" %
                          reverse('newsite'), response.content)

        site = Site.objects.create(name="testSite", institution_id="testInst", start_date=datetime.today())

        response = self.client.get(reverse('listsites'))
        self.assertNotContains(response, "testSite")

        site.users.add(User.objects.get(username="test0001"))

        response = self.client.get(reverse('listsites'))
        self.assertContains(response, "testSite")

    def test_view_show(self):
        response = self.client.get(reverse('showsite', kwargs={'site_id': 1}))
        self.assertEqual(response.status_code, 302)  # Not logged in, redirected to login
        self.assertTrue(response.url.endswith(
            '%s?next=%s' % (reverse('raven_login'), reverse('showsite', kwargs={'site_id': 1}))))

        do_test_login(self, user="test0001")

        response = self.client.get(reverse('showsite', kwargs={'site_id': 1}))
        self.assertEqual(response.status_code, 404)  # The Site does not exist

        NetworkConfig.objects.create(IPv4='131.111.58.253', IPv6='2001:630:212:8::8c:253', type='ipvxpub',
                                     name="mws-66424.mws3.csx.cam.ac.uk")

        NetworkConfig.objects.create(IPv4='172.28.18.253', type='ipv4priv',
                                     name='mws-46250.mws3.csx.private.cam.ac.uk')

        NetworkConfig.objects.create(IPv6='2001:630:212:8::8c:ff4', name='mws-client1', type='ipv6')

        site = Site.objects.create(name="testSite", institution_id="testInst", start_date=datetime.today())

        response = self.client.get(site.get_absolute_url())
        self.assertEqual(response.status_code, 403)  # The User is not in the list of auth users

        site.users.add(User.objects.get(username="test0001"))
        response = self.client.get(site.get_absolute_url())
        self.assertContains(response, "No billing details are available")

    def test_view_new(self):
        response = self.client.get(reverse('newsite'))
        self.assertEqual(response.status_code, 302)  # Not logged in, redirected to login
        self.assertTrue(response.url.endswith(
            '%s?next=%s' % (reverse('raven_login'), reverse('newsite'))))

        do_test_login(self, user="test0001")

        response = self.client.get(reverse('newsite'))
        self.assertRedirects(response, expected_url=reverse('listsites'))

        NetworkConfig.objects.create(IPv4='131.111.58.253', IPv6='2001:630:212:8::8c:253', type='ipvxpub',
                                     name="mws-66424.mws3.csx.cam.ac.uk")

        NetworkConfig.objects.create(IPv4='172.28.18.253', type='ipv4priv',
                                     name='mws-46250.mws3.csx.private.cam.ac.uk')

        NetworkConfig.objects.create(IPv6='2001:630:212:8::8c:ff4', name='mws-client1', type='ipv6')
        NetworkConfig.objects.create(IPv6='2001:630:212:8::8c:ff3', name='mws-client2', type='ipv6')
        NetworkConfig.objects.create(IPv6='2001:630:212:8::8c:ff2', name='mws-client3', type='ipv6')
        NetworkConfig.objects.create(IPv6='2001:630:212:8::8c:ff1', name='mws-client4', type='ipv6')

        response = self.client.get(reverse('newsite'))
        self.assertContains(response, "Request new site")

        response = self.client.post(reverse('newsite'), {'siteform-description': 'Desc',
                                                         'siteform-institution_id': 'UIS',
                                                         'siteform-email': 'amc203@cam.ac.uk'})
        self.assertContains(response, "This field is required.")  # Empty name, error

        response = self.client.post(reverse('newsite'), {'siteform-name': 'Test Site',
                                                         'siteform-description': 'Desc',
                                                         'siteform-institution_id': 'UIS',
                                                         'siteform-email': 'amc203@cam.ac.uk'})

        test_site = Site.objects.get(name='Test Site')
        self.assertRedirects(response, expected_url=test_site.get_absolute_url())

        # TODO test email check
        # TODO test dns api
        # TODO test errors

        self.assertEqual(test_site.email, 'amc203@cam.ac.uk')
        self.assertEqual(test_site.institution_id, 'UIS')
        self.assertEqual(test_site.description, 'Desc')

        response = self.client.get(response.url)

        self.assertContains(response, "Your email \'%s\' is still unconfirmed, please check your email inbox and "
                                      "click on the link of the email we sent you." % test_site.email)

        self.assertEqual(len(test_site.production_vms), 1)

        # Force post installation ACK

        with mock.patch("apimws.ansible.subprocess") as mock_subprocess:
            mock_subprocess.check_output.return_value.returncode = 0
            response = self.client.post(reverse(post_installation), {'vm': test_site.production_vms[0].id,
                                                                     'token': test_site.production_vms[0].token})
            self.assertIn(response.status_code, [200, 302])
            mock_subprocess.check_output.assert_called_with(["userv", "mws-admin", "mws_ansible_host",
                                                             test_site.production_service.virtual_machines.first()
                                                            .network_configuration.name])

        # Disable site
        self.assertFalse(test_site.disabled)
        self.client.post(reverse('disablesite', kwargs={'site_id': test_site.id}))
        # TODO test that views are restricted
        self.assertTrue(Site.objects.get(pk=test_site.id).disabled)
        # Enable site
        self.client.post(reverse('enablesite', kwargs={'site_id': test_site.id}))
        # TODO test that views are no longer restricted
        self.assertFalse(Site.objects.get(pk=test_site.id).disabled)

        self.assertEqual(len(test_site.test_vms), 0)

        # Clone first VM into the secondary VM
        self.client.post(reverse(views.clone_vm_view, kwargs={'site_id': test_site.id}), {'primary_vm': 'true'})

        self.assertEqual(len(test_site.test_vms), 1)

        self.client.delete(reverse(views.delete_vm, kwargs={'service_id': test_site.secondary_vm.service.id}))

        self.client.post(reverse('deletesite', kwargs={'site_id': test_site.id}))
        self.assertIsNone(Site.objects.get(pk=test_site.id).end_date)

        self.client.post(reverse('deletesite', kwargs={'site_id': test_site.id}), {'confirmation': 'yes'})
        self.assertIsNotNone(Site.objects.get(pk=test_site.id).end_date)

        test_site.delete()

    def test_view_edit(self):
        response = self.client.get(reverse('editsite', kwargs={'site_id': 1}))
        self.assertEqual(response.status_code, 302)  # Not logged in, redirected to login
        self.assertTrue(response.url.endswith(
            '%s?next=%s' % (reverse('raven_login'), reverse('editsite', kwargs={'site_id': 1}))))

        do_test_login(self, user="test0001")

        response = self.client.get(reverse('editsite', kwargs={'site_id': 1}))
        self.assertEqual(response.status_code, 404)  # The Site does not exist

        NetworkConfig.objects.create(IPv4='131.111.58.253', IPv6='2001:630:212:8::8c:253', type='ipvxpub',
                                     name="mws-66424.mws3.csx.cam.ac.uk")

        NetworkConfig.objects.create(IPv4='172.28.18.253', type='ipv4priv',
                                     name='mws-46250.mws3.csx.private.cam.ac.uk')

        NetworkConfig.objects.create(IPv6='2001:630:212:8::8c:ff4', name='mws-client1', type='ipv6')
        NetworkConfig.objects.create(IPv6='2001:630:212:8::8c:ff3', name='mws-client2', type='ipv6')
        NetworkConfig.objects.create(IPv6='2001:630:212:8::8c:ff2', name='mws-client3', type='ipv6')
        NetworkConfig.objects.create(IPv6='2001:630:212:8::8c:ff1', name='mws-client4', type='ipv6')

        site = Site.objects.create(name="testSite", institution_id="testInst", start_date=datetime.today())
        service = Service.objects.create(site=site, type='production', status="ready",
                                         network_configuration=NetworkConfig.get_free_prod_service_config())
        VirtualMachine.objects.create(name="test_vm", token=uuid.uuid4(),
                                      service=service, network_configuration=NetworkConfig.get_free_host_config())

        response = self.client.get(reverse('editsite', kwargs={'site_id': site.id}))
        self.assertEqual(response.status_code, 403)  # The User is not in the list of auth users

        site.users.add(User.objects.get(username="test0001"))
        response = self.client.get(reverse('editsite', kwargs={'site_id': site.id}))
        self.assertContains(response, "Managed Web Service account settings")

        suspension = site.suspend_now(input_reason="test suspension")
        response = self.client.get(reverse('editsite', kwargs={'site_id': site.id}))
        self.assertEqual(response.status_code, 403)  # The site is suspended

        suspension.active = False
        suspension.save()
        response = self.client.get(reverse('editsite', kwargs={'site_id': site.id}))
        self.assertContains(response, "Managed Web Service account settings")

        self.assertNotEqual(site.name, 'testSiteChange')
        self.assertNotEqual(site.description, 'testDescChange')
        self.assertNotEqual(site.institution_id, 'UIS')
        self.assertNotEqual(site.email, 'email@change.test')
        response = self.client.post(reverse('editsite', kwargs={'site_id': site.id}),
                                    {'name': 'testSiteChange', 'description': 'testDescChange',
                                     'institution_id': 'UIS', 'email': 'email@change.test'})
        self.assertRedirects(response, expected_url=site.get_absolute_url()) # Changes done, redirecting
        site_changed = Site.objects.get(pk=site.id)
        self.assertEqual(site_changed.name, 'testSiteChange')
        self.assertEqual(site_changed.description, 'testDescChange')
        self.assertEqual(site_changed.institution_id, 'UIS')
        self.assertEqual(site_changed.email, 'email@change.test')

        response = self.client.get(response.url)
        self.assertContains(response, "Your email \'%s\' is still unconfirmed, please check your email inbox and "
                                      "click on the link of the email we sent you." % site_changed.email)

    def test_view_billing(self):
        response = self.client.get(reverse(views.billing_management, kwargs={'site_id': 1}))
        self.assertEqual(response.status_code, 302)  # Not logged in, redirected to login
        self.assertTrue(response.url.endswith(
            '%s?next=%s' % (reverse('raven_login'), reverse(views.billing_management, kwargs={'site_id': 1}))))

        do_test_login(self, user="test0001")

        response = self.client.get(reverse(views.billing_management, kwargs={'site_id': 1}))
        self.assertEqual(response.status_code, 404)  # The Site does not exist

        NetworkConfig.objects.create(IPv4='131.111.58.253', IPv6='2001:630:212:8::8c:253', type='ipvxpub',
                                     name="mws-66424.mws3.csx.cam.ac.uk")

        NetworkConfig.objects.create(IPv4='172.28.18.253', type='ipv4priv',
                                     name='mws-46250.mws3.csx.private.cam.ac.uk')

        NetworkConfig.objects.create(IPv6='2001:630:212:8::8c:ff4', name='mws-client1', type='ipv6')
        NetworkConfig.objects.create(IPv6='2001:630:212:8::8c:ff3', name='mws-client2', type='ipv6')
        NetworkConfig.objects.create(IPv6='2001:630:212:8::8c:ff2', name='mws-client3', type='ipv6')
        NetworkConfig.objects.create(IPv6='2001:630:212:8::8c:ff1', name='mws-client4', type='ipv6')

        site = Site.objects.create(name="testSite", institution_id="testInst", start_date=datetime.today())
        service = Service.objects.create(site=site, type='production', status="ready",
                                         network_configuration=NetworkConfig.get_free_prod_service_config())
        VirtualMachine.objects.create(name="test_vm", token=uuid.uuid4(),
                                      service=service, network_configuration=NetworkConfig.get_free_host_config())

        response = self.client.get(reverse(views.billing_management, kwargs={'site_id': site.id}))
        self.assertEqual(response.status_code, 403)  # The User is not in the list of auth users

        site.users.add(User.objects.get(username="test0001"))
        response = self.client.get(reverse(views.billing_management, kwargs={'site_id': site.id}))
        self.assertContains(response, "Billing data")
        response = self.client.get(site.get_absolute_url())
        self.assertContains(response, "No billing details are available")

        suspension = site.suspend_now(input_reason="test suspension")
        response = self.client.get(reverse(views.billing_management, kwargs={'site_id': site.id}))
        self.assertEqual(response.status_code, 403)  # The site is suspended

        suspension.active = False
        suspension.save()
        response = self.client.get(reverse(views.billing_management, kwargs={'site_id': site.id}))
        self.assertContains(response, "Billing data")

        self.assertFalse(hasattr(site, 'billing'))
        with open(os.path.join(settings.BASE_DIR, 'requirements.txt')) as fp:
            response = self.client.post(reverse(views.billing_management, kwargs={'site_id': site.id}),
                                        {'purchase_order_number': 'testOrderNumber', 'group': 'testGroup',
                                         'purchase_order': fp})
        self.assertRedirects(response, expected_url=site.get_absolute_url())  # Changes done, redirecting
        site_changed = Site.objects.get(pk=site.id)
        self.assertEqual(site_changed.billing.purchase_order_number, 'testOrderNumber')
        self.assertEqual(site_changed.billing.group, 'testGroup')
        self.assertEqual(site_changed.billing.purchase_order.name, 'billing/requirements.txt')
        self.assertEqual(site_changed.billing.purchase_order.url, '/media/billing/requirements.txt')
        response = self.client.get(response.url)
        self.assertNotContains(response, "No Billing, please add one.")
        site_changed.billing.purchase_order.delete()

        site = Site.objects.get(pk=site.id)
        response = self.client.get(reverse(views.billing_management, kwargs={'site_id': site.id}))
        self.assertContains(response, "testOrderNumber")
        self.assertContains(response, "testGroup")
        self.assertTrue(hasattr(site, 'billing'))
        with open(os.path.join(settings.BASE_DIR, 'requirements.txt')) as fp:
            response = self.client.post(reverse(views.billing_management, kwargs={'site_id': site.id}),
                                        {'purchase_order_number': 'testOrderNumber1', 'group': 'testGroup1',
                                         'purchase_order': fp})
        self.assertRedirects(response, expected_url=site.get_absolute_url()) # Changes done, redirecting
        site_changed = Site.objects.get(pk=site.id)
        self.assertEqual(site_changed.billing.purchase_order_number, 'testOrderNumber1')
        self.assertEqual(site_changed.billing.group, 'testGroup1')
        self.assertEqual(site_changed.billing.purchase_order.name, 'billing/requirements.txt')
        self.assertEqual(site_changed.billing.purchase_order.url, '/media/billing/requirements.txt')
        response = self.client.get(response.url)
        self.assertNotContains(response, "No Billing, please add one.")
        site_changed.billing.purchase_order.delete()


@override_settings(CELERY_EAGER_PROPAGATES_EXCEPTIONS=True, CELERY_ALWAYS_EAGER=True, BROKER_BACKEND='memory')
class SiteManagement2Tests(TestCase):
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

    def create_site(self):
        site = Site.objects.create(name="testSite", institution_id="testInst", start_date=datetime.today())
        site.users.add(User.objects.get(username='test0001'))
        service = Service.objects.create(site=site, type='production', status="ready",
                                         network_configuration=NetworkConfig.get_free_prod_service_config())
        VirtualMachine.objects.create(name="test_vm", token=uuid.uuid4(),
                                      service=service, network_configuration=NetworkConfig.get_free_host_config())
        return site

    def test_no_permission_views_tests(self):
        site = Site.objects.create(name="testSite", institution_id="testInst", start_date=datetime.today())
        service = Service.objects.create(site=site, type='production', status="ready",
                                         network_configuration=NetworkConfig.get_free_prod_service_config())
        vm = VirtualMachine.objects.create(name="test_vm", token=uuid.uuid4(),
                                           service=service, network_configuration=NetworkConfig.get_free_host_config())
        vhost = Vhost.objects.create(name="tests_vhost", service=service)
        dn = DomainName.objects.create(name="testtestest.mws3.csx.cam.ac.uk", status="accepted", vhost=vhost)
        unix_group = UnixGroup.objects.create(name="testUnixGroup", service=service)

        # TODO test index empty
        self.assertEqual(self.client.get(site.get_absolute_url()).status_code, 403)
        self.assertEqual(self.client.get(reverse('editsite', kwargs={'site_id': site.id})).status_code, 403)
        self.assertEqual(self.client.get(reverse(views.service_settings,
                                                 kwargs={'service_id': service.id})).status_code, 403)
        self.assertEqual(self.client.get(reverse(views.billing_management,
                                                 kwargs={'site_id': site.id})).status_code, 403)
        self.assertEqual(self.client.get(reverse('deletesite', kwargs={'site_id': site.id})).status_code, 403)
        self.assertEqual(self.client.get(reverse('disablesite', kwargs={'site_id': site.id})).status_code, 403)
        self.assertEqual(self.client.get(reverse('enablesite', kwargs={'site_id': site.id})).status_code, 403)
        self.assertEqual(self.client.get(reverse('listvhost',
                                                 kwargs={'service_id': service.id})).status_code, 403)
        self.assertEqual(self.client.get(reverse('createvhost', kwargs={'service_id': service.id})).status_code, 403)
        self.assertEqual(self.client.get(reverse(views.system_packages,
                                                 kwargs={'service_id': service.id})).status_code, 403)
        self.assertEqual(self.client.get(reverse(views.clone_vm_view, kwargs={'site_id': site.id})).status_code, 403)
        self.assertEqual(self.client.get(reverse('mwsauth.views.auth_change',
                                                 kwargs={'site_id': site.id})).status_code, 403)
        self.assertEqual(self.client.get(reverse(views.delete_vm, kwargs={'service_id': service.id})).status_code, 403)
        self.assertEqual(self.client.get(reverse(views.power_vm, kwargs={'service_id': service.id})).status_code, 403)
        self.assertEqual(self.client.get(reverse(views.reset_vm, kwargs={'service_id': service.id})).status_code, 403)
        self.assertEqual(self.client.get(reverse(views.unix_groups,
                                                 kwargs={'service_id': service.id})).status_code, 403)
        self.assertEqual(self.client.get(reverse(views.unix_groups,
                                                 kwargs={'service_id': service.id})).status_code, 403)
        self.assertEqual(self.client.get(reverse(views.add_unix_group,
                                                 kwargs={'service_id': service.id})).status_code, 403)
        self.assertEqual(self.client.get(reverse(views.check_vm_status,
                                                 kwargs={'service_id': service.id})).status_code, 403)
        self.assertEqual(self.client.get(reverse('listvhost', kwargs={'service_id': service.id})).status_code, 403)
        self.assertEqual(self.client.get(reverse('listdomains',
                                                 kwargs={'vhost_id': vhost.id})).status_code, 403)
        self.assertEqual(self.client.get(reverse('deletevhost', kwargs={'vhost_id': vhost.id})).status_code, 403)
        self.assertEqual(self.client.get(reverse(views.certificates, kwargs={'vhost_id': vhost.id})).status_code, 403)
        self.assertEqual(self.client.get(reverse(views.add_domain, kwargs={'vhost_id': vhost.id})).status_code, 403)
        self.assertEqual(self.client.get(reverse('deletedomain', kwargs={'domain_id': dn.id})).status_code, 403)
        self.assertEqual(self.client.get(reverse(views.set_dn_as_main, kwargs={'domain_id': dn.id})).status_code, 403)
        self.assertEqual(self.client.get(reverse(views.unix_group, kwargs={'ug_id': unix_group.id})).status_code, 403)
        self.assertEqual(self.client.get(reverse(views.delete_unix_group,
                                                 kwargs={'ug_id': unix_group.id})).status_code, 403)

    def test_vm_is_busy(self):
        site = self.create_site()
        service = site.production_service
        service.status = "requested"
        service.save()
        service2 = Service.objects.create(site=site, type='test', status="requested",
                                          network_configuration=NetworkConfig.get_free_prod_service_config())
        VirtualMachine.objects.create(name="test_vm2", token=uuid.uuid4(), service=service2,
                                      network_configuration=NetworkConfig.get_free_host_config())
        vhost = Vhost.objects.create(name="tests_vhost", service=service)
        dn = DomainName.objects.create(name="testtestest.mws3.csx.cam.ac.uk", status="accepted", vhost=vhost)
        unix_group = UnixGroup.objects.create(name="testUnixGroup", service=service)

        # TODO test index not empty
        self.assertRedirects(self.client.get(reverse('editsite', kwargs={'site_id': site.id})),
                             expected_url=site.get_absolute_url())
        self.assertRedirects(self.client.get(reverse(views.service_settings, kwargs={'service_id': service.id})),
                             expected_url=site.get_absolute_url())
        self.assertEqual(self.client.get(reverse(views.billing_management, kwargs={'site_id': site.id})).status_code,
                         200)
        self.assertRedirects(self.client.get(reverse('deletesite', kwargs={'site_id': site.id})),
                             expected_url=site.get_absolute_url())
        self.assertRedirects(self.client.get(reverse('disablesite', kwargs={'site_id': site.id})),
                             expected_url=site.get_absolute_url())
        self.assertRedirects(self.client.get(reverse('enablesite', kwargs={'site_id': site.id})),
                             expected_url=reverse('listsites'))
        self.assertRedirects(self.client.get(reverse('listvhost', kwargs={'service_id': service.id})),
                             expected_url=site.get_absolute_url())
        self.assertRedirects(self.client.get(reverse('createvhost', kwargs={'service_id': service.id})),
                             expected_url=site.get_absolute_url())
        self.assertRedirects(self.client.get(reverse(views.system_packages, kwargs={'service_id': service.id})),
                             expected_url=site.get_absolute_url())
        self.assertRedirects(self.client.get(reverse(views.clone_vm_view, kwargs={'site_id': site.id})),
                             expected_url=site.get_absolute_url())
        self.assertRedirects(self.client.get(reverse('mwsauth.views.auth_change', kwargs={'site_id': site.id})),
                             expected_url=site.get_absolute_url())
        self.assertEqual(self.client.get(reverse(views.delete_vm, kwargs={'service_id': service.id})).status_code,
                         403) # Primary VM cannot be deleted
        self.assertRedirects(self.client.get(reverse(views.delete_vm, kwargs={'service_id': service2.id})),
                             expected_url=site.get_absolute_url())
        self.assertRedirects(self.client.get(reverse(views.power_vm, kwargs={'service_id': service.id})),
                             expected_url=site.get_absolute_url())
        self.assertRedirects(self.client.get(reverse(views.reset_vm, kwargs={'service_id': service.id})),
                             expected_url=site.get_absolute_url())
        self.assertRedirects(self.client.get(reverse(views.unix_groups, kwargs={'service_id': service.id})),
                             expected_url=site.get_absolute_url())
        self.assertRedirects(self.client.get(reverse(views.unix_groups, kwargs={'service_id': service.id})),
                             expected_url=site.get_absolute_url())
        self.assertRedirects(self.client.get(reverse(views.add_unix_group, kwargs={'service_id': service.id})),
                             expected_url=site.get_absolute_url())
        self.assertEqual(self.client.get(reverse(views.check_vm_status,
                                                 kwargs={'service_id': service.id})).status_code,
                         200)  # The error is shown in JSON format
        self.assertRedirects(self.client.get(reverse('listvhost', kwargs={'service_id': service.id})),
                             expected_url=site.get_absolute_url())
        self.assertRedirects(self.client.get(reverse('listdomains', kwargs={'vhost_id': vhost.id})),
                             expected_url=site.get_absolute_url())
        self.assertRedirects(self.client.get(reverse('deletevhost', kwargs={'vhost_id': vhost.id})),
                             expected_url=site.get_absolute_url())
        self.assertRedirects(self.client.get(reverse(views.certificates, kwargs={'vhost_id': vhost.id})),
                             expected_url=site.get_absolute_url())
        self.assertRedirects(self.client.get(reverse(views.add_domain, kwargs={'vhost_id': vhost.id})),
                             expected_url=site.get_absolute_url())
        self.assertRedirects(self.client.get(reverse('deletedomain', kwargs={'domain_id': dn.id})),
                             expected_url=site.get_absolute_url())
        self.assertRedirects(self.client.get(reverse(views.set_dn_as_main, kwargs={'domain_id': dn.id})),
                             expected_url=site.get_absolute_url())
        self.assertRedirects(self.client.get(reverse(views.unix_group, kwargs={'ug_id': unix_group.id})),
                             expected_url=site.get_absolute_url())
        self.assertRedirects(self.client.get(reverse(views.delete_unix_group, kwargs={'ug_id': unix_group.id})),
                             expected_url=site.get_absolute_url())

    def test_unix_groups(self):
        site = self.create_site()
        with mock.patch("apimws.ansible.subprocess") as mock_subprocess:
            mock_subprocess.check_output.return_value.returncode = 0
            response = self.client.post(reverse(views.add_unix_group,
                                                kwargs={'service_id': site.production_service.id}),
                                        {'unix_users': 'amc203,jw35', 'name': 'testUnixGroup'})
            self.assertIn(response.status_code, [200, 302])
            mock_subprocess.check_output.assert_called_with(["userv", "mws-admin", "mws_ansible_host",
                                                             site.production_service.virtual_machines.first()
                                                                 .network_configuration.name])
        response = self.client.get(response.url)
        self.assertInHTML('<td>testUnixGroup</td>', response.content)
        self.assertInHTML('<td>amc203, jw35</td>', response.content)
        unix_group = UnixGroup.objects.get(name='testUnixGroup')
        self.assertSequenceEqual([User.objects.get(username='amc203'), User.objects.get(username='jw35')],
                                 unix_group.users.all())

        response = self.client.get(reverse(views.unix_group, kwargs={'ug_id': unix_group.id}))
        self.assertInHTML('<input id="id_name" maxlength="16" name="name" type="text" value="testUnixGroup" />',
                          response.content)
        self.assertContains(response, 'crsid: "amc203"')
        self.assertContains(response, 'crsid: "jw35"')

        with mock.patch("apimws.ansible.subprocess") as mock_subprocess:
            mock_subprocess.check_output.return_value.returncode = 0
            response = self.client.post(reverse(views.unix_group, kwargs={'ug_id': unix_group.id}),
                                        {'unix_users': 'jw35', 'name': 'testUnixGroup2'})
            mock_subprocess.check_output.assert_called_with(["userv", "mws-admin", "mws_ansible_host",
                                                             site.production_service.virtual_machines.first()
                                                                 .network_configuration.name])
        response = self.client.get(response.url)
        self.assertInHTML('<td>testUnixGroup2</td>', response.content, count=1)
        self.assertInHTML('<td>testUnixGroup</td>', response.content, count=0)
        self.assertInHTML('<td>jw35</td>', response.content, count=1)
        self.assertInHTML('<td>amc203</td>', response.content, count=0)

        with mock.patch("apimws.ansible.subprocess") as mock_subprocess:
            mock_subprocess.check_output.return_value.returncode = 0
            response = self.client.delete(reverse(views.delete_unix_group, kwargs={'ug_id': unix_group.id}))
            mock_subprocess.check_output.assert_called_with(["userv", "mws-admin", "mws_ansible_host",
                                                             site.production_service.virtual_machines.first()
                                                                 .network_configuration.name])
        response = self.client.get(response.url)
        self.assertInHTML('<td>testUnixGroup2</td>', response.content, count=0)
        self.assertInHTML('<td>jw35</td>', response.content, count=0)

    def test_vhosts_list(self):
        site = self.create_site()
        with mock.patch("apimws.ansible.subprocess") as mock_subprocess:
            mock_subprocess.check_output.return_value.returncode = 0
            response = self.client.post(reverse('createvhost', kwargs={'service_id': site.production_service.id}),
                                        {'name': 'testVhost'})
            self.assertIn(response.status_code, [200, 302])
            mock_subprocess.check_output.assert_called_with(["userv", "mws-admin", "mws_ansible_host",
                                                             site.production_service.virtual_machines.first()
                                                                 .network_configuration.name])
        self.assertRedirects(response,
                             expected_url=reverse('listvhost', kwargs={'service_id': site.production_service.id}))
        response = self.client.get(reverse('listvhost', kwargs={'service_id': site.production_service.id}))
        self.assertInHTML('<td>testVhost</td>', response.content)
        vhost = Vhost.objects.get(name='testVhost')
        self.assertSequenceEqual([vhost], site.production_service.vhosts.all())

        with mock.patch("apimws.ansible.subprocess") as mock_subprocess:
            mock_subprocess.check_output.return_value.returncode = 0
            response = self.client.delete(reverse('deletevhost', kwargs={'vhost_id': vhost.id}))
            mock_subprocess.check_output.assert_called_with(["userv", "mws-admin", "mws_ansible_host",
                                                             site.production_service.virtual_machines.first()
                                                                 .network_configuration.name])
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('listvhost', kwargs={'service_id': site.production_service.id}))
        self.assertInHTML('<td>testVhost</td>', response.content, count=0)

    def test_domains_management(self):
        site = self.create_site()

        with mock.patch("apimws.ansible.subprocess") as mock_subprocess:
            mock_subprocess.check_output.return_value.returncode = 0
            self.client.post(reverse('createvhost', kwargs={'service_id': site.production_service.id}),
                             {'name': 'testVhost'})

            vhost = Vhost.objects.get(name='testVhost')

            self.client.get(reverse(views.add_domain, kwargs={'vhost_id': vhost.id}))  # TODO check it
            response = self.client.post(reverse(views.add_domain, kwargs={'vhost_id': vhost.id}),
                                        {'name': 'test.mws3.csx.cam.ac.uk'})
            self.assertIn(response.status_code, [200, 302])
            mock_subprocess.check_output.assert_called_with(["userv", "mws-admin", "mws_ansible_host",
                                                             site.production_service.virtual_machines.first()
                                                                 .network_configuration.name])

        response = self.client.get(reverse('listdomains', kwargs={'vhost_id': vhost.id}))
        self.assertInHTML('<tbody><tr><td><p>test.mws3.csx.cam.ac.uk</p></td><td><p>Requested</p></td>'
                          '<td><p>Managed domain name</p></td><td style="width: 155px; cursor: pointer"><p>'
                          '<a onclick="javascript:ajax_call(\'/set_dn_as_main/1/\', \'POST\')">Set as main domain</a>'
                          '<a class="delete_domain" data-href="javascript:ajax_call(\'/delete_domain/1/\', \'DELETE\')"'
                          '> <i title="Delete" class="fa fa-trash-o fa-2x" data-toggle="tooltip"></i></a></p></td>'
                          '</tr></tbody>',
                          response.content, count=1)
        self.client.get(reverse(views.set_dn_as_main, kwargs={'domain_id': 1}))
        self.assertInHTML('<tbody><tr><td><p>test.mws3.csx.cam.ac.uk</p></td><td><p>Requested</p></td>'
                          '<td><p>Managed domain name</p></td>'
                          '<td style="width: 155px; cursor: pointer"><p><a onclick="javascript:ajax_call'
                          '(\'/set_dn_as_main/1/\', \'POST\')">Set as main domain</a><a class="delete_domain" '
                          'data-href="javascript:ajax_call(\'/delete_domain/1/\', \'DELETE\')"> <i '
                          'title="Delete" class="fa fa-trash-o fa-2x" data-toggle="tooltip"></i></a></p></td></tr>'
                          '</tbody>', response.content, count=1)
        with mock.patch("apimws.ansible.subprocess") as mock_subprocess:
            mock_subprocess.check_output.return_value.returncode = 0
            response = self.client.post(reverse(views.set_dn_as_main, kwargs={'domain_id': 1}))
            mock_subprocess.check_output.assert_called_with(["userv", "mws-admin", "mws_ansible_host",
                                                             site.production_service.virtual_machines.first()
                                                                 .network_configuration.name])
        response = self.client.get(reverse('listdomains', kwargs={'vhost_id': vhost.id}))
        self.assertInHTML('<tbody><tr><td><p>test.mws3.csx.cam.ac.uk<br>This is the current main domain</p></td>'
                          '<td><p>Requested</p></td> <td><p>Managed domain name</p></td>'
                          '<td style="width: 155px; cursor: pointer"><p><a onclick="javascript:ajax_call'
                          '(\'/set_dn_as_main/1/\', \'POST\')">Set as main domain</a><a class="delete_domain" '
                          'data-href="javascript:ajax_call(\'/delete_domain/1/\', \'DELETE\')"> <i '
                          'title="Delete" class="fa fa-trash-o fa-2x" data-toggle="tooltip"></i></a></p></td></tr>'
                          '</tbody>', response.content, count=1)
        with mock.patch("apimws.ansible.subprocess") as mock_subprocess:
            mock_subprocess.check_output.return_value.returncode = 0
            response = self.client.delete(reverse('deletedomain', kwargs={'domain_id': 1}))
            mock_subprocess.check_output.assert_called_with(["userv", "mws-admin", "mws_ansible_host",
                                                             site.production_service.virtual_machines.first()
                                                                 .network_configuration.name])
        response = self.client.get(reverse('listdomains', kwargs={'vhost_id': vhost.id}))
        self.assertInHTML('<tbody><tr><td><p>test.mws3.csx.cam.ac.uk<br>This is the current main domain</p></td>'
                          '<td><p>Requested</p></td><td><p>Managed domain name</p></td>'
                          '<td style="width: 155px; cursor: pointer"><p><a onclick="javascript:ajax_call'
                          '(\'/set_dn_as_main/1/\', \'POST\')">Set as main domain</a><a class="delete_domain" '
                          'data-href="javascript:ajax_call(\'/delete_domain/1/\', \'DELETE\')"> <i '
                          'title="Delete" class="fa fa-trash-o fa-2x" data-toggle="tooltip"></i></a></p></td></tr>'
                          '</tbody>', response.content, count=0)
        with mock.patch("apimws.ansible.subprocess") as mock_subprocess:
            mock_subprocess.check_output.return_value.returncode = 0
            response = self.client.post(reverse(views.add_domain, kwargs={'vhost_id': vhost.id}),
                                        {'name': 'externaldomain.com'})
            mock_subprocess.check_output.assert_called_with(["userv", "mws-admin", "mws_ansible_host",
                                                             site.production_service.virtual_machines.first()
                                                                 .network_configuration.name])
        response = self.client.get(response.url)
        self.assertInHTML('<tr><td><p>externaldomain.com</p></td><td><p>Accepted</p></td>'
                          '<td><p><a class="setup_instructions" style="cursor: pointer;">Set up instructions</a></p>'
                          '</td><td style="width: 155px; cursor: pointer"><p><a onclick="javascript:ajax_call'
                          '(\'/set_dn_as_main/2/\', \'POST\')">Set as main domain</a><a class="delete_domain" '
                          'data-href="javascript:ajax_call(\'/delete_domain/2/\', \'DELETE\')"> <i '
                          'title="Delete" class="fa fa-trash-o fa-2x" data-toggle="tooltip"></i></a></p></td></tr>',
                          response.content, count=1)

    def test_system_packages(self):
        site = self.create_site()
        with mock.patch("apimws.ansible.subprocess") as mock_subprocess:
            mock_subprocess.check_output.return_value.returncode = 0
            response = self.client.post(reverse(views.system_packages,
                                                kwargs={'service_id': site.production_service.id}),
                                        {'package_number': 1})
            self.assertEqual(response.status_code, 200)
            mock_subprocess.check_output.assert_called_with(["userv", "mws-admin", "mws_ansible_host",
                                                             site.production_service.virtual_machines.first()
                                                                 .network_configuration.name])
        self.assertEqual(AnsibleConfiguration.objects.get(key="system_packages").value, "1")
        self.assertContains(response, "Wordpress &lt;installed&gt;")

        with mock.patch("apimws.ansible.subprocess") as mock_subprocess:
            mock_subprocess.check_output.return_value.returncode = 0
            response = self.client.post(reverse(views.system_packages,
                                                kwargs={'service_id': site.production_service.id}),
                                        {'package_number': 2})
            mock_subprocess.check_output.assert_called_with(["userv", "mws-admin", "mws_ansible_host",
                                                             site.production_service.virtual_machines.first()
                                                                 .network_configuration.name])
        self.assertEqual(AnsibleConfiguration.objects.get(key="system_packages").value, "1,2")
        self.assertContains(response, "Wordpress &lt;installed&gt;")
        self.assertContains(response, "Drupal &lt;installed&gt;")
        with mock.patch("apimws.ansible.subprocess") as mock_subprocess:
            mock_subprocess.check_output.return_value.returncode = 0
            self.client.post(reverse(views.system_packages, kwargs={'service_id': site.production_service.id}),
                             {'package_number': 1})
            mock_subprocess.check_output.assert_called_with(["userv", "mws-admin", "mws_ansible_host",
                                                             site.production_service.virtual_machines.first()
                                                                 .network_configuration.name])
        self.assertEqual(AnsibleConfiguration.objects.get(key="system_packages").value, "2")

    # def test_certificates(self):
    #     site = self.create_site()
    #
    #     with mock.patch("apimws.ansible.subprocess") as mock_subprocess:
    #         mock_subprocess.check_output.return_value.returncode = 0
    #         response = self.client.post(reverse('createvhost', kwargs={'service_id': site.production_service.id}),
    #                                     {'name': 'testVhost'})
    #         self.assertIn(response.status_code, [200, 302])
    #         mock_subprocess.check_output.assert_called_with(["userv", "mws-admin", "mws_ansible"])
    #
    #     vhost = Vhost.objects.get(name='testVhost')
    #     response = self.client.post(reverse(views.generate_csr, kwargs={'vhost_id': vhost.id}))
    #     self.assertContains(response, "A CSR couldn't be generated because you don't have a master domain assigned to "
    #                                   "this vhost.")
    #     self.assertIsNone(vhost.csr)
    #
    #     with mock.patch("apimws.ansible.subprocess") as mock_subprocess:
    #         mock_subprocess.check_output.return_value.returncode = 0
    #         self.client.post(reverse(views.add_domain, kwargs={'vhost_id': vhost.id}), {'name': 'randomdomain.co.uk'})
    #         self.assertEqual(response.status_code, 200)
    #         mock_subprocess.check_output.assert_called_with(["userv", "mws-admin", "mws_ansible"])
    #
    #     vhost = Vhost.objects.get(name='testVhost')
    #     self.assertIsNone(vhost.csr)
    #     self.assertIsNone(vhost.certificate)
    #     self.assertIsNotNone(vhost.main_domain)
    #     self.client.post(reverse(views.generate_csr, kwargs={'vhost_id': vhost.id}))
    #     vhost = Vhost.objects.get(name='testVhost')
    #     self.assertIsNotNone(vhost.csr)
    #
    #     privatekeyfile = tempfile.NamedTemporaryFile()
    #     csrfile = tempfile.NamedTemporaryFile()
    #     certificatefile = tempfile.NamedTemporaryFile()
    #     subprocess.check_output(["openssl", "req", "-new", "-newkey", "rsa:2048", "-nodes", "-keyout",
    #                              privatekeyfile.name, "-subj", "/C=GB/CN=%s" % vhost.main_domain.name,
    #                              "-out", csrfile.name])
    #     subprocess.check_output(["openssl", "x509", "-req", "-days", "365", "-in", csrfile.name, "-signkey",
    #                              privatekeyfile.name, "-out", certificatefile.name])
    #
    #     certificatefiledesc = open(certificatefile.name, 'r')
    #     privatekeyfiledesc = open(privatekeyfile.name, 'r')
    #     self.client.post(reverse(views.certificates, kwargs={'vhost_id': vhost.id}),
    #                      {'key': privatekeyfile, 'cert': certificatefile})
    #     certificatefiledesc.close()
    #     privatekeyfiledesc.close()
    #     vhost = Vhost.objects.get(name='testVhost')
    #     self.assertIsNotNone(vhost.certificate)
    #
    #     certificatefile.seek(0)
    #     self.assertEqual(vhost.certificate, certificatefile.read())
    #
    #     privatekeyfile.seek(0)
    #     response = self.client.post(reverse(views.certificates, kwargs={'vhost_id': vhost.id}),
    #                                 {'cert': privatekeyfile})
    #     self.assertContains(response, "The certificate file is invalid")
    #
    #     certificatefile.seek(0)
    #     response = self.client.post(reverse(views.certificates, kwargs={'vhost_id': vhost.id}),
    #                                 {'key': certificatefile})
    #     self.assertContains(response, "The key file is invalid")
    #
    #     privatekeyfile.close()
    #     privatekeyfile = tempfile.NamedTemporaryFile()
    #     subprocess.check_output(["openssl", "genrsa", "-out", privatekeyfile.name, "2048"])
    #
    #     certificatefile.seek(0)
    #     response = self.client.post(reverse(views.certificates, kwargs={'vhost_id': vhost.id}),
    #                                 {'key': privatekeyfile, 'cert': certificatefile})
    #     self.assertContains(response, "The key doesn&#39;t match the certificate")
    #
    #     privatekeyfile.close()
    #     csrfile.close()
    #     certificatefile.close()

    def test_backups(self):
        site = self.create_site()

        with mock.patch("apimws.ansible.subprocess") as mock_subprocess:
            mock_subprocess.check_output.return_value.returncode = 0
            response = self.client.post(reverse('createvhost', kwargs={'service_id': site.production_service.id}),
                                        {'name': 'testVhost'})
            self.assertIn(response.status_code, [200, 302])
            vhost = Vhost.objects.get(name='testVhost')
            response = self.client.post(reverse(views.add_domain, kwargs={'vhost_id': vhost.id}),
                                        {'name': 'testDomain.cam.ac.uk'})
            self.assertIn(response.status_code, [200, 302])
            mock_subprocess.check_output.assert_called_with(["userv", "mws-admin", "mws_ansible_host",
                                                             site.production_service.virtual_machines.first()
                                                                 .network_configuration.name])

        restore_date = datetime.now()

        with reversion.create_revision():
            domain = DomainName.objects.get(name='testDomain.cam.ac.uk')
            domain.name = "error"
            domain.status = 'accepted'
            domain.save()

        self.client.post(reverse(views.backups, kwargs={'service_id': vhost.service.id}), {'backupdate': restore_date})
        domain = DomainName.objects.get(name='testDomain.cam.ac.uk')
        self.assertEqual(domain.status, 'accepted')
        self.assertEqual(domain.name, 'testDomain.cam.ac.uk')
