from datetime import datetime
import uuid
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.urlresolvers import reverse
from django.test import TestCase, override_settings
from mwsauth.tests import do_test_login
from sitesmanagement.models import NetworkConfig, Site, VirtualMachine, Service
from sitesmanagement.views import billing_management


@override_settings(CELERY_EAGER_PROPAGATES_EXCEPTIONS=True, CELERY_ALWAYS_EAGER=True, BROKER_BACKEND='memory')
class BillingTests(TestCase):

    def test_view_billing(self):
        response = self.client.get(reverse(billing_management, kwargs={'site_id': 1}))
        self.assertEqual(response.status_code, 302)  # Not logged in, redirected to login
        self.assertTrue(response.url.endswith(
            '%s?next=%s' % (reverse('raven_login'), reverse(billing_management, kwargs={'site_id': 1}))))

        do_test_login(self, user="test0001")

        response = self.client.get(reverse(billing_management, kwargs={'site_id': 1}))
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

        response = self.client.get(reverse(billing_management, kwargs={'site_id': site.id}))
        self.assertEqual(response.status_code, 403)  # The User is not in the list of auth users

        site.users.add(User.objects.get(username="test0001"))
        response = self.client.get(reverse(billing_management, kwargs={'site_id': site.id}))
        self.assertContains(response, "Billing data")
        response = self.client.get(site.get_absolute_url())
        self.assertContains(response, "No billing details are available")

        suspension = site.suspend_now(input_reason="test suspension")
        response = self.client.get(reverse(billing_management, kwargs={'site_id': site.id}))
        self.assertEqual(response.status_code, 403)  # The site is suspended

        suspension.active = False
        suspension.save()
        response = self.client.get(reverse(billing_management, kwargs={'site_id': site.id}))
        self.assertContains(response, "Billing data")

        self.assertFalse(hasattr(site, 'billing'))
        pofile = SimpleUploadedFile("file.pdf", "file_content")
        response = self.client.post(reverse(billing_management, kwargs={'site_id': site.id}),
                                    {'purchase_order_number': 'testOrderNumber', 'group': 'testGroup',
                                     'purchase_order': pofile})
        self.assertRedirects(response, expected_url=site.get_absolute_url())  # Changes done, redirecting
        site_changed = Site.objects.get(pk=site.id)
        self.assertEqual(site_changed.billing.purchase_order_number, 'testOrderNumber')
        self.assertEqual(site_changed.billing.group, 'testGroup')
        self.assertEqual(site_changed.billing.purchase_order.name, 'billing/file.pdf')
        self.assertEqual(site_changed.billing.purchase_order.url, '/media/billing/file.pdf')
        response = self.client.get(response.url)
        self.assertNotContains(response, "No Billing, please add one.")
        site_changed.billing.purchase_order.delete()

        site = Site.objects.get(pk=site.id)
        response = self.client.get(reverse(billing_management, kwargs={'site_id': site.id}))
        self.assertContains(response, "testOrderNumber")
        self.assertContains(response, "testGroup")
        self.assertTrue(hasattr(site, 'billing'))
        pofile = SimpleUploadedFile("file.pdf", "file_content")
        response = self.client.post(reverse(billing_management, kwargs={'site_id': site.id}),
                                    {'purchase_order_number': 'testOrderNumber1', 'group': 'testGroup1',
                                     'purchase_order': pofile})
        self.assertRedirects(response, expected_url=site.get_absolute_url())  # Changes done, redirecting
        site_changed = Site.objects.get(pk=site.id)
        self.assertEqual(site_changed.billing.purchase_order_number, 'testOrderNumber1')
        self.assertEqual(site_changed.billing.group, 'testGroup1')
        self.assertEqual(site_changed.billing.purchase_order.name, 'billing/file.pdf')
        self.assertEqual(site_changed.billing.purchase_order.url, '/media/billing/file.pdf')
        response = self.client.get(response.url)
        self.assertNotContains(response, "No Billing, please add one.")
        site_changed.billing.purchase_order.delete()
