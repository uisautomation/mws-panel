from datetime import datetime
import tempfile
import uuid
import mock
import os
from django.conf import settings
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test import TestCase, override_settings
from django.utils import unittest
import subprocess
import reversion
from apimws.models import AnsibleConfiguration
from apimws.views import post_installation
from mwsauth.tests import do_test_login
from sitesmanagement.models import ServiceNetworkConfig, Site, VirtualMachine, UnixGroup, Vhost, DomainName, \
    HostNetworkConfig
import sitesmanagement.views as views
from sitesmanagement.utils import is_camacuk, get_object_or_None


@override_settings(CELERY_EAGER_PROPAGATES_EXCEPTIONS=True, CELERY_ALWAYS_EAGER=True, BROKER_BACKEND='memory')
class SiteManagementTests(TestCase):

    def test_is_camacuk_helper(self):
        self.assertTrue(is_camacuk("www.cam.ac.uk"))
        self.assertFalse(is_camacuk("www.com.ac.uk"))

    def test_get_object_or_none(self):
        self.assertIsNone(get_object_or_None(User, username="test0001"))
        User.objects.create_user(username="test0001")
        self.assertIsNotNone(get_object_or_None(User, username="test0001"))

    def test_view_index(self):
        response = self.client.get(reverse(views.index))
        self.assertEqual(response.status_code, 302)  # Not logged in, redirected to login
        self.assertTrue(response.url.endswith(
            '%s?next=%s' % (reverse('raven_login'), reverse(views.index))))

        do_test_login(self, user="test0001")

        response = self.client.get(reverse(views.index))
        self.assertInHTML("<p class=\"campl-notifications-icon campl-warning-icon\" style=\"float:none; margin-bottom: "
                          "10px;\">At this moment we cannot process any new request for the Managed Web Service, please"
                          " try again later.</p>", response.content)

        netconf = ServiceNetworkConfig.objects.create(IPv4='131.111.58.255', IPv6='2001:630:212:8::8c:255',
                                                      IPv4private='172.28.18.255',
                                                      mws_private_domain='mws-08246.mws3.csx.private.ca.ac.uk',
                                                      mws_domain="mws-12940.mws3.csx.cam.ac.uk")
        self.assertInHTML("<p class=\"campl-notifications-icon campl-warning-icon\" style=\"float:none; margin-bottom: "
                          "10px;\">At this moment we cannot process any new request for the Managed Web Service, please"
                          " try again later.</p>", response.content)
        HostNetworkConfig.objects.create(IPv6='2001:db8:212:8::8d:255')

        response = self.client.get(reverse(views.index))
        self.assertInHTML("<p><a href=\"%s\" class=\"campl-primary-cta\">Register new server</a></p>" %
                          reverse(views.new), response.content)

        site = Site.objects.create(name="testSite", institution_id="testinst", start_date=datetime.today(),
                                   service_network_configuration=netconf)

        response = self.client.get(reverse(views.index))
        self.assertNotContains(response, "testSite")

        site.users.add(User.objects.get(username="test0001"))

        response = self.client.get(reverse(views.index))
        self.assertContains(response, "testSite")

    def test_view_show(self):
        response = self.client.get(reverse(views.show, kwargs={'site_id': 1}))
        self.assertEqual(response.status_code, 302)  # Not logged in, redirected to login
        self.assertTrue(response.url.endswith(
            '%s?next=%s' % (reverse('raven_login'), reverse(views.show, kwargs={'site_id': 1}))))

        do_test_login(self, user="test0001")

        response = self.client.get(reverse(views.show, kwargs={'site_id': 1}))
        self.assertEqual(response.status_code, 404)  # The Site does not exist

        netconf = ServiceNetworkConfig.objects.create(IPv4='131.111.58.255', IPv6='2001:630:212:8::8c:255',
                                                      IPv4private='172.28.18.255',
                                                      mws_private_domain='mws-08246.mws3.csx.private.ca.ac.uk',
                                                      mws_domain="mws-12940.mws3.csx.cam.ac.uk")

        site = Site.objects.create(name="testSite", institution_id="testinst", start_date=datetime.today(),
                                   service_network_configuration=netconf)
        response = self.client.get(reverse(views.show, kwargs={'site_id': site.id}))
        self.assertEqual(response.status_code, 403)  # The User is not in the list of auth users

        site.users.add(User.objects.get(username="test0001"))
        response = self.client.get(reverse(views.show, kwargs={'site_id': site.id}))
        self.assertContains(response, "No billing details are available")

    @unittest.skipUnless(hasattr(settings, 'PLATFORMS_API_USERNAME'), "Platforms API login details not available.")
    def test_view_new(self):
        response = self.client.get(reverse(views.new))
        self.assertEqual(response.status_code, 302)  # Not logged in, redirected to login
        self.assertTrue(response.url.endswith(
            '%s?next=%s' % (reverse('raven_login'), reverse(views.new))))

        do_test_login(self, user="test0001")

        response = self.client.get(reverse(views.new))
        self.assertEqual(response.status_code, 302)  # There aren't prealocated network configurations
        self.assertTrue(response.url.endswith(reverse(views.index)))

        ServiceNetworkConfig.objects.create(IPv4='131.111.58.255', IPv6='2001:630:212:8::8c:255',
                                            IPv4private='172.28.18.255',
                                            mws_private_domain='mws-08246.mws3.csx.private.ca.ac.uk',
                                            mws_domain="mws-12940.mws3.csx.cam.ac.uk")

        HostNetworkConfig.objects.create(IPv6='2001:630:212:8::8c:254', name='mws-client1')
        HostNetworkConfig.objects.create(IPv6='2001:630:212:8::8c:253', name='mws-client2')
        HostNetworkConfig.objects.create(IPv6='2001:630:212:8::8c:252', name='mws-client3')
        HostNetworkConfig.objects.create(IPv6='2001:630:212:8::8c:251', name='mws-client4')

        response = self.client.get(reverse(views.new))
        self.assertContains(response, "Request new site")

        response = self.client.post(reverse(views.new), {'siteform-description': 'Desc',
                                                         'siteform-institution_id': 'UIS',
                                                         'siteform-email': 'amc203@cam.ac.uk'})
        self.assertContains(response, "This field is required.")  # Empty name, error

        response = self.client.post(reverse(views.new), {'siteform-name': 'Test Site',
                                                         'siteform-description': 'Desc',
                                                         'siteform-institution_id': 'UIS',
                                                         'siteform-email': 'amc203@cam.ac.uk'})

        test_site = Site.objects.get(name='Test Site')
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith(reverse(views.show, kwargs={'site_id': test_site.id})))

        # TODO test platforms API
        # TODO test email check
        # TODO test dns api
        # TODO test errors

        self.assertEqual(test_site.email, 'amc203@cam.ac.uk')
        self.assertEqual(test_site.institution_id, 'UIS')
        self.assertEqual(test_site.description, 'Desc')

        response = self.client.get(response.url)

        self.assertContains(response, "Your email \'%s\' is still unconfirmed, please check your email inbox and "
                                      "click on the link of the email we sent you." % test_site.email)

        # Force post installation ACK
        self.client.post(reverse(post_installation), {'vm': test_site.primary_vm.id,
                                                      'token': test_site.primary_vm.token})

        # Disable site
        self.assertFalse(test_site.disabled)
        self.client.post(reverse(views.disable, kwargs={'site_id': test_site.id}))
        # TODO test that views are restricted
        self.assertTrue(Site.objects.get(pk=test_site.id).disabled)
        # Enable site
        self.client.post(reverse(views.enable, kwargs={'site_id': test_site.id}))
        # TODO test that views are no longer restricted
        self.assertFalse(Site.objects.get(pk=test_site.id).disabled)

        # Clone first VM into the secondary VM
        self.client.post(reverse(views.clone_vm_view, kwargs={'site_id': test_site.id}), {'primary_vm': 'true'})
        secondary_vm = test_site.secondary_vm
        secondary_vm.status = 'ready'
        secondary_vm.save()

        self.client.delete(reverse(views.delete_vm, kwargs={'vm_id': test_site.secondary_vm.id}))

        self.client.post(reverse(views.delete, kwargs={'site_id': test_site.id}))
        self.assertIsNone(Site.objects.get(pk=test_site.id).end_date)

        self.client.post(reverse(views.delete, kwargs={'site_id': test_site.id}), {'confirmation': 'yes'})
        self.assertIsNotNone(Site.objects.get(pk=test_site.id).end_date)

        test_site.delete()

    def test_view_edit(self):
        response = self.client.get(reverse(views.edit, kwargs={'site_id': 1}))
        self.assertEqual(response.status_code, 302)  # Not logged in, redirected to login
        self.assertTrue(response.url.endswith(
            '%s?next=%s' % (reverse('raven_login'), reverse(views.edit, kwargs={'site_id': 1}))))

        do_test_login(self, user="test0001")

        response = self.client.get(reverse(views.edit, kwargs={'site_id': 1}))
        self.assertEqual(response.status_code, 404)  # The Site does not exist

        netconf = ServiceNetworkConfig.objects.create(IPv4='131.111.58.255', IPv6='2001:630:212:8::8c:255',
                                                      IPv4private='172.28.18.255',
                                                      mws_private_domain='mws-08246.mws3.csx.private.ca.ac.uk',
                                                      mws_domain="mws-12940.mws3.csx.cam.ac.uk")
        site = Site.objects.create(name="testSite", institution_id="testInst", start_date=datetime.today(),
                                   service_network_configuration=netconf)
        VirtualMachine.objects.create(name="test_vm", primary=True, status="ready", token=uuid.uuid4(), site=site,
                                      network_configuration=HostNetworkConfig.objects.
                                      create(IPv6=netconf.IPv6, name=netconf.mws_domain))
        response = self.client.get(reverse(views.edit, kwargs={'site_id': site.id}))
        self.assertEqual(response.status_code, 403)  # The User is not in the list of auth users

        site.users.add(User.objects.get(username="test0001"))
        response = self.client.get(reverse(views.edit, kwargs={'site_id': site.id}))
        self.assertContains(response, "Managed Web Service account settings")

        suspension = site.suspend_now(input_reason="test suspension")
        response = self.client.get(reverse(views.edit, kwargs={'site_id': site.id}))
        self.assertEqual(response.status_code, 403)  # The site is suspended

        suspension.active = False
        suspension.save()
        response = self.client.get(reverse(views.edit, kwargs={'site_id': site.id}))
        self.assertContains(response, "Managed Web Service account settings")

        self.assertNotEqual(site.name, 'testSiteChange')
        self.assertNotEqual(site.description, 'testDescChange')
        self.assertNotEqual(site.institution_id, 'UIS')
        self.assertNotEqual(site.email, 'email@change.test')
        response = self.client.post(reverse(views.edit, kwargs={'site_id': site.id}),
                                    {'name': 'testSiteChange', 'description': 'testDescChange',
                                     'institution_id': 'UIS', 'email': 'email@change.test'})
        self.assertEqual(response.status_code, 302)  # Changes done, redirecting
        self.assertTrue(response.url.endswith(reverse(views.show, kwargs={'site_id': site.id})))
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

        netconf = ServiceNetworkConfig.objects.create(IPv4='131.111.58.255', IPv6='2001:630:212:8::8c:255',
                                                      IPv4private='172.28.18.255',
                                                      mws_private_domain='mws-08246.mws3.csx.private.ca.ac.uk',
                                                      mws_domain="mws-12940.mws3.csx.cam.ac.uk")
        site = Site.objects.create(name="testSite", institution_id="testInst", start_date=datetime.today(),
                                   service_network_configuration=netconf)
        response = self.client.get(reverse(views.billing_management, kwargs={'site_id': site.id}))
        self.assertEqual(response.status_code, 403)  # The User is not in the list of auth users

        site.users.add(User.objects.get(username="test0001"))
        response = self.client.get(reverse(views.billing_management, kwargs={'site_id': site.id}))
        self.assertContains(response, "Billing data")
        response = self.client.get(reverse(views.show, kwargs={'site_id': site.id}))
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
        self.assertEqual(response.status_code, 302)  # Changes done, redirecting
        self.assertTrue(response.url.endswith(reverse(views.show, kwargs={'site_id': site.id})))
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
        self.assertEqual(response.status_code, 302)  # Changes done, redirecting
        self.assertTrue(response.url.endswith(reverse(views.show, kwargs={'site_id': site_changed.id})))
        site_changed = Site.objects.get(pk=site.id)
        self.assertEqual(site_changed.billing.purchase_order_number, 'testOrderNumber1')
        self.assertEqual(site_changed.billing.group, 'testGroup1')
        self.assertEqual(site_changed.billing.purchase_order.name, 'billing/requirements.txt')
        self.assertEqual(site_changed.billing.purchase_order.url, '/media/billing/requirements.txt')
        response = self.client.get(response.url)
        self.assertNotContains(response, "No Billing, please add one.")
        site_changed.billing.purchase_order.delete()

    def test_no_permission_views_tests(self):
        do_test_login(self, user="test0001")
        netconf = ServiceNetworkConfig.objects.create(IPv4='131.111.58.255', IPv6='2001:630:212:8::8c:255',
                                                      IPv4private='172.28.18.255',
                                                      mws_private_domain='mws-08246.mws3.csx.private.ca.ac.uk',
                                                      mws_domain="mws-12940.mws3.csx.cam.ac.uk")
        site = Site.objects.create(name="testSite", institution_id="testInst", start_date=datetime.today(),
                                   service_network_configuration=netconf)
        vm = VirtualMachine.objects.create(name="test_vm", primary=True, status="ready", token=uuid.uuid4(), site=site,
                                           network_configuration=HostNetworkConfig.objects.
                                           create(IPv6=netconf.IPv6, name=netconf.mws_domain))
        vhost = Vhost.objects.create(name="tests_vhost", vm=vm)
        dn = DomainName.objects.create(name="testtestest.mws3.csx.cam.ac.uk", status="accepted", vhost=vhost)
        unix_group = UnixGroup.objects.create(name="testUnixGroup", vm=vm)

        # TODO test index empty
        response = self.client.get(reverse(views.show, kwargs={'site_id': site.id}))
        self.assertEqual(response.status_code, 403)
        response = self.client.get(reverse(views.edit, kwargs={'site_id': site.id}))
        self.assertEqual(response.status_code, 403)
        response = self.client.get(reverse(views.settings, kwargs={'vm_id': vm.id}))
        self.assertEqual(response.status_code, 403)
        response = self.client.get(reverse(views.billing_management, kwargs={'site_id': site.id}))
        self.assertEqual(response.status_code, 403)
        response = self.client.get(reverse(views.delete, kwargs={'site_id': site.id}))
        self.assertEqual(response.status_code, 403)
        response = self.client.get(reverse(views.disable, kwargs={'site_id': site.id}))
        self.assertEqual(response.status_code, 403)
        response = self.client.get(reverse(views.enable, kwargs={'site_id': site.id}))
        self.assertEqual(response.status_code, 403)
        response = self.client.get(reverse(views.vhosts_management, kwargs={'vm_id': vm.id}))
        self.assertEqual(response.status_code, 403)
        response = self.client.get(reverse(views.add_vhost, kwargs={'vm_id': vm.id}))
        self.assertEqual(response.status_code, 403)
        response = self.client.get(reverse(views.system_packages, kwargs={'vm_id': vm.id}))
        self.assertEqual(response.status_code, 403)
        response = self.client.get(reverse(views.clone_vm_view, kwargs={'site_id': site.id}))
        self.assertEqual(response.status_code, 403)
        response = self.client.get(reverse('mwsauth.views.auth_change', kwargs={'site_id': site.id}))
        self.assertEqual(response.status_code, 403)
        response = self.client.get(reverse(views.delete_vm, kwargs={'vm_id': vm.id}))
        self.assertEqual(response.status_code, 403)
        response = self.client.get(reverse(views.power_vm, kwargs={'vm_id': vm.id}))
        self.assertEqual(response.status_code, 403)
        response = self.client.get(reverse(views.reset_vm, kwargs={'vm_id': vm.id}))
        self.assertEqual(response.status_code, 403)
        response = self.client.get(reverse(views.unix_groups, kwargs={'vm_id': vm.id}))
        self.assertEqual(response.status_code, 403)
        response = self.client.get(reverse(views.unix_groups, kwargs={'vm_id': vm.id}))
        self.assertEqual(response.status_code, 403)
        response = self.client.get(reverse(views.add_unix_group, kwargs={'vm_id': vm.id}))
        self.assertEqual(response.status_code, 403)
        response = self.client.get(reverse(views.check_vm_status, kwargs={'vm_id': vm.id}))
        self.assertEqual(response.status_code, 403)
        response = self.client.get(reverse(views.vhosts_management, kwargs={'vm_id': vm.id}))
        self.assertEqual(response.status_code, 403)
        response = self.client.get(reverse(views.domains_management, kwargs={'vhost_id': vhost.id}))
        self.assertEqual(response.status_code, 403)
        response = self.client.get(reverse(views.delete_vhost, kwargs={'vhost_id': vhost.id}))
        self.assertEqual(response.status_code, 403)
        response = self.client.get(reverse(views.certificates, kwargs={'vhost_id': vhost.id}))
        self.assertEqual(response.status_code, 403)
        response = self.client.get(reverse(views.add_domain, kwargs={'vhost_id': vhost.id}))
        self.assertEqual(response.status_code, 403)
        response = self.client.get(reverse(views.delete_dn, kwargs={'domain_id': dn.id}))
        self.assertEqual(response.status_code, 403)
        response = self.client.get(reverse(views.set_dn_as_main, kwargs={'domain_id': dn.id}))
        self.assertEqual(response.status_code, 403)
        response = self.client.get(reverse(views.unix_group, kwargs={'ug_id': unix_group.id}))
        self.assertEqual(response.status_code, 403)
        response = self.client.get(reverse(views.delete_unix_group, kwargs={'ug_id': unix_group.id}))
        self.assertEqual(response.status_code, 403)

    def test_vm_is_busy(self):
        do_test_login(self, user="test0001")
        netconf = ServiceNetworkConfig.objects.create(IPv4='131.111.58.255', IPv6='2001:630:212:8::8c:255',
                                                      IPv4private='172.28.18.255',
                                                      mws_private_domain='mws-08246.mws3.csx.private.ca.ac.uk',
                                                      mws_domain="mws-12940.mws3.csx.cam.ac.uk")
        site = Site.objects.create(name="testSite", institution_id="testInst", start_date=datetime.today(),
                                   service_network_configuration=netconf)
        site.users.add(User.objects.get(username='test0001'))
        vm = VirtualMachine.objects.create(name="test_vm", primary=True, status="requested", token=uuid.uuid4(),
                                           site=site, network_configuration=HostNetworkConfig.objects.
                                           create(IPv6=netconf.IPv6, name=netconf.mws_domain))
        vm2 = VirtualMachine.objects.create(name="test_vm2", primary=False, status="requested", token=uuid.uuid4(),
                                            site=site, network_configuration=HostNetworkConfig.objects.
                                            create(IPv6='2001:630:212:8::8c:254', name=netconf.mws_private_domain))
        vhost = Vhost.objects.create(name="tests_vhost", vm=vm)
        dn = DomainName.objects.create(name="testtestest.mws3.csx.cam.ac.uk", status="accepted", vhost=vhost)
        unix_group = UnixGroup.objects.create(name="testUnixGroup", vm=vm)

        # TODO test index not empty
        response = self.client.get(reverse(views.edit, kwargs={'site_id': site.id}))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith('%s' % (reverse(views.show, kwargs={'site_id': site.id}))))
        response = self.client.get(reverse(views.settings, kwargs={'vm_id': vm.id}))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith('%s' % (reverse(views.show, kwargs={'site_id': site.id}))))
        response = self.client.get(reverse(views.billing_management, kwargs={'site_id': site.id}))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse(views.delete, kwargs={'site_id': site.id}))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith('%s' % (reverse(views.show, kwargs={'site_id': site.id}))))
        response = self.client.get(reverse(views.disable, kwargs={'site_id': site.id}))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith('%s' % (reverse(views.show, kwargs={'site_id': site.id}))))
        response = self.client.get(reverse(views.enable, kwargs={'site_id': site.id}))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith('%s' % (reverse(views.index))))
        response = self.client.get(reverse(views.vhosts_management, kwargs={'vm_id': vm.id}))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith('%s' % (reverse(views.show, kwargs={'site_id': site.id}))))
        response = self.client.get(reverse(views.add_vhost, kwargs={'vm_id': vm.id}))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith('%s' % (reverse(views.show, kwargs={'site_id': site.id}))))
        response = self.client.get(reverse(views.system_packages, kwargs={'vm_id': vm.id}))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith('%s' % (reverse(views.show, kwargs={'site_id': site.id}))))
        response = self.client.get(reverse(views.clone_vm_view, kwargs={'site_id': site.id}))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith('%s' % (reverse(views.show, kwargs={'site_id': site.id}))))
        response = self.client.get(reverse('mwsauth.views.auth_change', kwargs={'site_id': site.id}))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse(views.delete_vm, kwargs={'vm_id': vm.id}))
        self.assertEqual(response.status_code, 403)  # Primary VM cannot be deleted
        response = self.client.get(reverse(views.delete_vm, kwargs={'vm_id': vm2.id}))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith('%s' % (reverse(views.show, kwargs={'site_id': site.id}))))
        response = self.client.get(reverse(views.power_vm, kwargs={'vm_id': vm.id}))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith('%s' % (reverse(views.show, kwargs={'site_id': site.id}))))
        response = self.client.get(reverse(views.reset_vm, kwargs={'vm_id': vm.id}))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith('%s' % (reverse(views.show, kwargs={'site_id': site.id}))))
        response = self.client.get(reverse(views.unix_groups, kwargs={'vm_id': vm.id}))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith('%s' % (reverse(views.show, kwargs={'site_id': site.id}))))
        response = self.client.get(reverse(views.unix_groups, kwargs={'vm_id': vm.id}))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith('%s' % (reverse(views.show, kwargs={'site_id': site.id}))))
        response = self.client.get(reverse(views.add_unix_group, kwargs={'vm_id': vm.id}))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith('%s' % (reverse(views.show, kwargs={'site_id': site.id}))))
        response = self.client.get(reverse(views.check_vm_status, kwargs={'vm_id': vm.id}))
        self.assertEqual(response.status_code, 200)  # The error is shown in JSON format
        response = self.client.get(reverse(views.vhosts_management, kwargs={'vm_id': vm.id}))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith('%s' % (reverse(views.show, kwargs={'site_id': site.id}))))
        response = self.client.get(reverse(views.domains_management, kwargs={'vhost_id': vhost.id}))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith('%s' % (reverse(views.show, kwargs={'site_id': site.id}))))
        response = self.client.get(reverse(views.delete_vhost, kwargs={'vhost_id': vhost.id}))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith('%s' % (reverse(views.show, kwargs={'site_id': site.id}))))
        response = self.client.get(reverse(views.certificates, kwargs={'vhost_id': vhost.id}))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith('%s' % (reverse(views.show, kwargs={'site_id': site.id}))))
        response = self.client.get(reverse(views.add_domain, kwargs={'vhost_id': vhost.id}))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith('%s' % (reverse(views.show, kwargs={'site_id': site.id}))))
        response = self.client.get(reverse(views.delete_dn, kwargs={'domain_id': dn.id}))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith('%s' % (reverse(views.show, kwargs={'site_id': site.id}))))
        response = self.client.get(reverse(views.set_dn_as_main, kwargs={'domain_id': dn.id}))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith('%s' % (reverse(views.show, kwargs={'site_id': site.id}))))
        response = self.client.get(reverse(views.unix_group, kwargs={'ug_id': unix_group.id}))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith('%s' % (reverse(views.show, kwargs={'site_id': site.id}))))
        response = self.client.get(reverse(views.delete_unix_group, kwargs={'ug_id': unix_group.id}))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith('%s' % (reverse(views.show, kwargs={'site_id': site.id}))))

    def create_site(self):
        netconf = ServiceNetworkConfig.objects.create(IPv4='131.111.58.255', IPv6='2001:630:212:8::8c:255',
                                                      IPv4private='172.28.18.255',
                                                      mws_private_domain='mws-08246.mws3.csx.private.ca.ac.uk',
                                                      mws_domain="mws-12940.mws3.csx.cam.ac.uk")
        site = Site.objects.create(name="testSite", institution_id="testInst", start_date=datetime.today(),
                                   service_network_configuration=netconf)
        site.users.add(User.objects.get(username='test0001'))
        VirtualMachine.objects.create(name="test_vm", primary=True, status="ready", token=uuid.uuid4(), site=site,
                                      network_configuration=HostNetworkConfig.objects.
                                      create(IPv6=netconf.IPv6, name=netconf.mws_domain))
        return site

    def test_unix_groups(self):
        do_test_login(self, user="test0001")
        site = self.create_site()
        with mock.patch("apimws.ansible.subprocess") as mock_subprocess:
            mock_subprocess.check_output.return_value.returncode = 0
            response = self.client.post(reverse(views.add_unix_group, kwargs={'vm_id': site.primary_vm.id}),
                                        {'unix_users': 'amc203,jw35', 'name': 'testUnixGroup'})
            self.assertIn(response.status_code, [200, 302])
            mock_subprocess.check_output.assert_called_with(["userv", "mws-admin", "mws_ansible"])
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
            mock_subprocess.check_output.assert_called_with(["userv", "mws-admin", "mws_ansible"])
        response = self.client.get(response.url)
        self.assertInHTML('<td>testUnixGroup2</td>', response.content, count=1)
        self.assertInHTML('<td>testUnixGroup</td>', response.content, count=0)
        self.assertInHTML('<td>jw35</td>', response.content, count=1)
        self.assertInHTML('<td>amc203</td>', response.content, count=0)

        with mock.patch("apimws.ansible.subprocess") as mock_subprocess:
            mock_subprocess.check_output.return_value.returncode = 0
            response = self.client.delete(reverse(views.delete_unix_group, kwargs={'ug_id': unix_group.id}))
            mock_subprocess.check_output.assert_called_with(["userv", "mws-admin", "mws_ansible"])
        response = self.client.get(response.url)
        self.assertInHTML('<td>testUnixGroup2</td>', response.content, count=0)
        self.assertInHTML('<td>jw35</td>', response.content, count=0)

    def test_vhosts_management(self):
        do_test_login(self, user="test0001")
        site = self.create_site()
        with mock.patch("apimws.ansible.subprocess") as mock_subprocess:
            mock_subprocess.check_output.return_value.returncode = 0
            response = self.client.post(reverse(views.add_vhost, kwargs={'vm_id': site.primary_vm.id}),
                                        {'name': 'testVhost'})
            self.assertIn(response.status_code, [200, 302])
            mock_subprocess.check_output.assert_called_with(["userv", "mws-admin", "mws_ansible"])
        response = self.client.get(response.url)  # TODO assert that url is vhost_management
        self.assertInHTML('<td>testVhost</td>', response.content)
        vhost = Vhost.objects.get(name='testVhost')
        self.assertSequenceEqual([vhost], site.primary_vm.vhosts.all())

        with mock.patch("apimws.ansible.subprocess") as mock_subprocess:
            mock_subprocess.check_output.return_value.returncode = 0
            response = self.client.delete(reverse(views.delete_vhost, kwargs={'vhost_id': vhost.id}))
            mock_subprocess.check_output.assert_called_with(["userv", "mws-admin", "mws_ansible"])
        response = self.client.get(response.url)  # TODO assert that url is vhost_management
        self.assertInHTML('<td>testVhost</td>', response.content, count=0)

    def test_domains_management(self):
        do_test_login(self, user="test0001")
        site = self.create_site()

        with mock.patch("apimws.ansible.subprocess") as mock_subprocess:
            mock_subprocess.check_output.return_value.returncode = 0
            self.client.post(reverse(views.add_vhost, kwargs={'vm_id': site.primary_vm.id}), {'name': 'testVhost'})

            vhost = Vhost.objects.get(name='testVhost')

            self.client.get(reverse(views.add_domain, kwargs={'vhost_id': vhost.id}))  # TODO check it
            response = self.client.post(reverse(views.add_domain, kwargs={'vhost_id': vhost.id}),
                                        {'name': 'test.mws3.csx.cam.ac.uk'})
            self.assertIn(response.status_code, [200, 302])
            mock_subprocess.check_output.assert_called_with(["userv", "mws-admin", "mws_ansible"])

        response = self.client.get(response.url)  # TODO assert that url is domains_management
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
            mock_subprocess.check_output.assert_called_with(["userv", "mws-admin", "mws_ansible"])
        response = self.client.get(response.url)
        self.assertInHTML('<tbody><tr><td><p>test.mws3.csx.cam.ac.uk<br>This is the current main domain</p></td>'
                          '<td><p>Requested</p></td> <td><p>Managed domain name</p></td>'
                          '<td style="width: 155px; cursor: pointer"><p><a onclick="javascript:ajax_call'
                          '(\'/set_dn_as_main/1/\', \'POST\')">Set as main domain</a><a class="delete_domain" '
                          'data-href="javascript:ajax_call(\'/delete_domain/1/\', \'DELETE\')"> <i '
                          'title="Delete" class="fa fa-trash-o fa-2x" data-toggle="tooltip"></i></a></p></td></tr>'
                          '</tbody>', response.content, count=1)
        with mock.patch("apimws.ansible.subprocess") as mock_subprocess:
            mock_subprocess.check_output.return_value.returncode = 0
            response = self.client.delete(reverse(views.delete_dn, kwargs={'domain_id': 1}))
            mock_subprocess.check_output.assert_called_with(["userv", "mws-admin", "mws_ansible"])
        response = self.client.get(response.url)
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
            mock_subprocess.check_output.assert_called_with(["userv", "mws-admin", "mws_ansible"])
        response = self.client.get(response.url)
        self.assertInHTML('<tr><td><p>externaldomain.com</p></td><td><p>Accepted</p></td>'
                          '<td><p><a id="setup_instructions" style="cursor: pointer;">Set up instructions</a></p></td>'
                          '<td style="width: 155px; cursor: pointer"><p><a onclick="javascript:ajax_call'
                          '(\'/set_dn_as_main/2/\', \'POST\')">Set as main domain</a><a class="delete_domain" '
                          'data-href="javascript:ajax_call(\'/delete_domain/2/\', \'DELETE\')"> <i '
                          'title="Delete" class="fa fa-trash-o fa-2x" data-toggle="tooltip"></i></a></p></td></tr>',
                          response.content, count=1)

    def test_system_packages(self):
        do_test_login(self, user="test0001")
        site = self.create_site()
        with mock.patch("apimws.ansible.subprocess") as mock_subprocess:
            mock_subprocess.check_output.return_value.returncode = 0
            response = self.client.post(reverse(views.system_packages, kwargs={'vm_id': site.primary_vm.id}),
                                        {'package_number': 1})
            self.assertEqual(response.status_code, 200)
            mock_subprocess.check_output.assert_called_with(["userv", "mws-admin", "mws_ansible"])
        self.assertEqual(AnsibleConfiguration.objects.get(key="system_packages").value, "1")
        self.assertContains(response, "Wordpress &lt;installed&gt;")

        with mock.patch("apimws.ansible.subprocess") as mock_subprocess:
            mock_subprocess.check_output.return_value.returncode = 0
            response = self.client.post(reverse(views.system_packages, kwargs={'vm_id': site.primary_vm.id}),
                                        {'package_number': 2})
            mock_subprocess.check_output.assert_called_with(["userv", "mws-admin", "mws_ansible"])
        self.assertEqual(AnsibleConfiguration.objects.get(key="system_packages").value, "1,2")
        self.assertContains(response, "Wordpress &lt;installed&gt;")
        self.assertContains(response, "Drupal &lt;installed&gt;")
        with mock.patch("apimws.ansible.subprocess") as mock_subprocess:
            mock_subprocess.check_output.return_value.returncode = 0
            self.client.post(reverse(views.system_packages, kwargs={'vm_id': site.primary_vm.id}),
                             {'package_number': 1})
            mock_subprocess.check_output.assert_called_with(["userv", "mws-admin", "mws_ansible"])
        self.assertEqual(AnsibleConfiguration.objects.get(key="system_packages").value, "2")

    def test_certificates(self):
        do_test_login(self, user="test0001")
        site = self.create_site()

        with mock.patch("apimws.ansible.subprocess") as mock_subprocess:
            mock_subprocess.check_output.return_value.returncode = 0
            response = self.client.post(reverse(views.add_vhost, kwargs={'vm_id': site.primary_vm.id}),
                                        {'name': 'testVhost'})
            self.assertIn(response.status_code, [200, 302])
            mock_subprocess.check_output.assert_called_with(["userv", "mws-admin", "mws_ansible"])

        vhost = Vhost.objects.get(name='testVhost')
        response = self.client.post(reverse(views.generate_csr, kwargs={'vhost_id': vhost.id}))
        self.assertContains(response, "A CSR couldn't be generated because you don't have a master domain assigned to "
                                      "this vhost.")
        self.assertIsNone(vhost.csr)

        with mock.patch("apimws.ansible.subprocess") as mock_subprocess:
            mock_subprocess.check_output.return_value.returncode = 0
            self.client.post(reverse(views.add_domain, kwargs={'vhost_id': vhost.id}), {'name': 'randomdomain.co.uk'})
            self.assertEqual(response.status_code, 200)
            mock_subprocess.check_output.assert_called_with(["userv", "mws-admin", "mws_ansible"])

        vhost = Vhost.objects.get(name='testVhost')
        self.assertIsNone(vhost.csr)
        self.assertIsNone(vhost.certificate)
        self.assertIsNotNone(vhost.main_domain)
        self.client.post(reverse(views.generate_csr, kwargs={'vhost_id': vhost.id}))
        vhost = Vhost.objects.get(name='testVhost')
        self.assertIsNotNone(vhost.csr)

        privatekeyfile = tempfile.NamedTemporaryFile()
        csrfile = tempfile.NamedTemporaryFile()
        certificatefile = tempfile.NamedTemporaryFile()
        subprocess.check_output(["openssl", "req", "-new", "-newkey", "rsa:2048", "-nodes", "-keyout",
                                 privatekeyfile.name, "-subj", "/C=GB/CN=%s" % vhost.main_domain.name,
                                 "-out", csrfile.name])
        subprocess.check_output(["openssl", "x509", "-req", "-days", "365", "-in", csrfile.name, "-signkey",
                                 privatekeyfile.name, "-out", certificatefile.name])

        certificatefiledesc = open(certificatefile.name, 'r')
        privatekeyfiledesc = open(privatekeyfile.name, 'r')
        self.client.post(reverse(views.certificates, kwargs={'vhost_id': vhost.id}),
                         {'key': privatekeyfile, 'cert': certificatefile})
        certificatefiledesc.close()
        privatekeyfiledesc.close()
        vhost = Vhost.objects.get(name='testVhost')
        self.assertIsNotNone(vhost.certificate)

        certificatefile.seek(0)
        self.assertEqual(vhost.certificate, certificatefile.read())

        privatekeyfile.seek(0)
        response = self.client.post(reverse(views.certificates, kwargs={'vhost_id': vhost.id}),
                                    {'cert': privatekeyfile})
        self.assertContains(response, "The certificate file is invalid")

        certificatefile.seek(0)
        response = self.client.post(reverse(views.certificates, kwargs={'vhost_id': vhost.id}),
                                    {'key': certificatefile})
        self.assertContains(response, "The key file is invalid")

        privatekeyfile.close()
        privatekeyfile = tempfile.NamedTemporaryFile()
        subprocess.check_output(["openssl", "genrsa", "-out", privatekeyfile.name, "2048"])

        certificatefile.seek(0)
        response = self.client.post(reverse(views.certificates, kwargs={'vhost_id': vhost.id}),
                                    {'key': privatekeyfile, 'cert': certificatefile})
        self.assertContains(response, "The key doesn&#39;t match the certificate")

        privatekeyfile.close()
        csrfile.close()
        certificatefile.close()

    def test_backups(self):
        do_test_login(self, user="test0001")
        site = self.create_site()

        with mock.patch("apimws.ansible.subprocess") as mock_subprocess:
            mock_subprocess.check_output.return_value.returncode = 0
            response = self.client.post(reverse(views.add_vhost, kwargs={'vm_id': site.primary_vm.id}),
                                        {'name': 'testVhost'})
            self.assertIn(response.status_code, [200, 302])
            vhost = Vhost.objects.get(name='testVhost')
            response = self.client.post(reverse(views.add_domain, kwargs={'vhost_id': vhost.id}),
                                        {'name': 'testDomain.cam.ac.uk'})
            self.assertIn(response.status_code, [200, 302])
            mock_subprocess.check_output.assert_called_with(["userv", "mws-admin", "mws_ansible"])

        restore_date = datetime.now()

        with reversion.create_revision():
            domain = DomainName.objects.get(name='testDomain.cam.ac.uk')
            domain.name = "error"
            domain.status = 'accepted'
            domain.save()

        self.client.post(reverse(views.backups, kwargs={'vm_id': vhost.vm.id}), {'backupdate': restore_date})
        domain = DomainName.objects.get(name='testDomain.cam.ac.uk')
        self.assertEqual(domain.status, 'accepted')
        self.assertEqual(domain.name, 'testDomain.cam.ac.uk')
