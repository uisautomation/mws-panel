import uuid
import mock
from datetime import datetime, timedelta, date
from django.contrib.auth.models import User
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.urlresolvers import reverse
from django.test import TestCase, override_settings

from apimws.models import Cluster, Host
from apimws.xen import which_cluster
from mwsauth.tests import do_test_login
from sitesmanagement.cronjobs import send_reminder_renewal, check_subscription
from sitesmanagement.models import NetworkConfig, Site, VirtualMachine, Service, Billing, Vhost


@override_settings(CELERY_EAGER_PROPAGATES_EXCEPTIONS=True, CELERY_ALWAYS_EAGER=True, BROKER_BACKEND='memory')
class BillingTests(TestCase):

    def test_view_billing(self):
        response = self.client.get(reverse('billing_management', kwargs={'site_id': 1}))
        self.assertEqual(response.status_code, 302)  # Not logged in, redirected to login
        self.assertTrue(response.url.endswith(
            '%s?next=%s' % (reverse('raven_login'), reverse('billing_management', kwargs={'site_id': 1}))))

        do_test_login(self, user="test0001")

        response = self.client.get(reverse('billing_management', kwargs={'site_id': 1}))
        self.assertEqual(response.status_code, 404)  # The Site does not exist

        cluster = Cluster.objects.create(name="mws-test-1")
        Host.objects.create(hostname="mws-test-1.dev.mws3.cam.ac.uk", cluster=cluster)

        NetworkConfig.objects.create(IPv4='131.111.58.253', IPv6='2001:630:212:8::8c:253', type='ipvxpub',
                                     name="mws-66424.mws3.csx.cam.ac.uk")

        NetworkConfig.objects.create(IPv4='172.28.18.253', type='ipv4priv',
                                     name='mws-46250.mws3.csx.private.cam.ac.uk')

        NetworkConfig.objects.create(IPv6='2001:630:212:8::8c:ff4', name='mws-client1', type='ipv6')
        NetworkConfig.objects.create(IPv6='2001:630:212:8::8c:ff3', name='mws-client2', type='ipv6')
        NetworkConfig.objects.create(IPv6='2001:630:212:8::8c:ff2', name='mws-client3', type='ipv6')
        NetworkConfig.objects.create(IPv6='2001:630:212:8::8c:ff1', name='mws-client4', type='ipv6')

        site = Site.objects.create(name="testSite", start_date=datetime.today())
        service = Service.objects.create(site=site, type='production', status="ready",
                                         network_configuration=NetworkConfig.get_free_prod_service_config())
        VirtualMachine.objects.create(name="test_vm", token=uuid.uuid4(), cluster=which_cluster(),
                                      service=service, network_configuration=NetworkConfig.get_free_host_config())
        Vhost.objects.create(name="default", service=service)

        response = self.client.get(reverse('billing_management', kwargs={'site_id': site.id}))
        self.assertEqual(response.status_code, 403)  # The User is not in the list of auth users

        site.users.add(User.objects.get(username="test0001"))
        response = self.client.get(reverse('billing_management', kwargs={'site_id': site.id}))
        self.assertContains(response, "Billing data")
        response = self.client.get(site.get_absolute_url())
        self.assertContains(response, "No billing details are available")

        with mock.patch("apimws.vm.change_vm_power_state") as mock_change_vm_power_state:
            mock_change_vm_power_state.return_value = True
            mock_change_vm_power_state.delay.return_value = True
            site.disable()

        suspension = site.suspend_now(input_reason="test suspension")
        response = self.client.get(reverse('billing_management', kwargs={'site_id': site.id}))
        self.assertEqual(response.status_code, 403)  # The site is suspended

        with mock.patch("apimws.vm.change_vm_power_state") as mock_change_vm_power_state:
            mock_change_vm_power_state.return_value = True
            mock_change_vm_power_state.delay.return_value = True
            with mock.patch("apimws.ansible.subprocess") as mock_subprocess:
                mock_subprocess.check_output.return_value.returncode = 0
                site.enable()

        suspension.start_date = datetime.today() - timedelta(days=2)
        suspension.end_date = datetime.today() - timedelta(days=1)
        suspension.save()
        response = self.client.get(reverse('billing_management', kwargs={'site_id': site.id}))
        self.assertContains(response, "Billing data")

        self.assertFalse(hasattr(site, 'billing'))
        pofile = SimpleUploadedFile("file.pdf", "file_content")
        response = self.client.post(reverse('billing_management', kwargs={'site_id': site.id}),
                                    {'purchase_order_number': 'testOrderNumber', 'group': 'testGroup',
                                     'purchase_order': pofile})
        self.assertRedirects(response, expected_url=site.get_absolute_url())  # Changes done, redirecting
        site_changed = Site.objects.get(pk=site.id)
        self.assertEqual(site_changed.billing.purchase_order_number, 'testOrderNumber')
        self.assertEqual(site_changed.billing.group, 'testGroup')
        self.assertRegexpMatches(site_changed.billing.purchase_order.name, 'billing/file.*\.pdf')
        self.assertRegexpMatches(site_changed.billing.purchase_order.url, '/media/billing/file.*\.pdf')
        response = self.client.get(response.url)
        self.assertNotContains(response, "No Billing, please add one.")
        site_changed.billing.purchase_order.delete()

        site = Site.objects.get(pk=site.id)
        response = self.client.get(reverse('billing_management', kwargs={'site_id': site.id}))
        self.assertContains(response, "testOrderNumber")
        self.assertContains(response, "testGroup")
        self.assertTrue(hasattr(site, 'billing'))
        pofile = SimpleUploadedFile("file.pdf", "file_content")
        response = self.client.post(reverse('billing_management', kwargs={'site_id': site.id}),
                                    {'purchase_order_number': 'testOrderNumber1', 'group': 'testGroup1',
                                     'purchase_order': pofile})
        self.assertRedirects(response, expected_url=site.get_absolute_url())  # Changes done, redirecting
        site_changed = Site.objects.get(pk=site.id)
        self.assertEqual(site_changed.billing.purchase_order_number, 'testOrderNumber1')
        self.assertEqual(site_changed.billing.group, 'testGroup1')
        self.assertRegexpMatches(site_changed.billing.purchase_order.name, 'billing/file.*\.pdf')
        self.assertRegexpMatches(site_changed.billing.purchase_order.url, '/media/billing/file.*\.pdf')
        response = self.client.get(response.url)
        self.assertNotContains(response, "No Billing, please add one.")
        site_changed.billing.purchase_order.delete()

    def test_renewals_emails(self):
        # 1 month for renewal warning
        today = datetime.today()
        site = Site.objects.create(name="testSite", email='amc203@cam.ac.uk',
                                   start_date=date(year=today.year-1, day=15,
                                                   month=today.month-1 if today.month!=1 else 12))
        pofile = SimpleUploadedFile("file.pdf", "file_content")
        Billing.objects.create(site=site, purchase_order_number='0000', purchase_order=pofile, group='test')
        send_reminder_renewal()
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject,
                         'The annual charge for your managed web server is due next month')
        self.assertEqual(mail.outbox[0].to, [site.email])

        # same month renewal warning
        site.start_date = site.start_date + timedelta(days=30)
        site.save()
        send_reminder_renewal()
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(mail.outbox[1].subject,
                         'REMINDER: the annual charge for your managed web server is due this month')
        self.assertEqual(mail.outbox[1].to, [site.email])

    def test_check_cacnel_if_not_paid(self):
        ''' This test checks that if the user does not uploads a PO before 30 days, the site will be cancelled
        automatically'''
        # 1 month for renewal warning
        today = datetime.today()
        site = Site.objects.create(name="testSite", email='amc203@cam.ac.uk',
                                   start_date=today-timedelta(days=10))
        User.objects.create(username="test0001")
        site.users.add(User.objects.get(username="test0001"))
        check_subscription()
        # Nothing should happen, only 10 days
        # Retrieve object
        site = Site.objects.get(pk=site.id)
        self.assertEqual(len(mail.outbox), 0)
        self.assertIsNone(site.end_date)
        self.assertTrue(site.subscription)
        self.assertTrue(site.users.exists())

        # 15 days reminder
        site.start_date = today - timedelta(days=15)
        site.save()
        check_subscription()
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject,
                         'Remember to upload a purchase order for your managed web server')
        self.assertEqual(mail.outbox[0].to, [site.email])
        # Retrieve object
        site = Site.objects.get(pk=site.id)
        self.assertIsNone(site.end_date)
        self.assertTrue(site.subscription)
        self.assertTrue(site.users.exists())

        # 20 days reminder (nothing)
        site.start_date = today - timedelta(days=20)
        site.save()
        check_subscription()
        self.assertEqual(len(mail.outbox), 1)
        # Retrieve object
        site = Site.objects.get(pk=site.id)
        self.assertIsNone(site.end_date)
        self.assertTrue(site.subscription)
        self.assertTrue(site.users.exists())

        # 25 days reminder, last week reminder
        site.start_date = today - timedelta(days=25)
        site.save()
        check_subscription()
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(mail.outbox[1].subject,
                         'Remember to upload a purchase order for your managed web server')
        self.assertEqual(mail.outbox[1].to, [site.email])
        # Retrieve object
        site = Site.objects.get(pk=site.id)
        self.assertIsNone(site.end_date)
        self.assertTrue(site.subscription)
        self.assertTrue(site.users.exists())

        # More tha 30 days, cancel the site
        site.start_date = today - timedelta(days=35)
        site.save()
        self.assertIsNone(site.end_date)
        self.assertIn(User.objects.get(username='test0001'), site.users.all())
        check_subscription()
        self.assertEqual(len(mail.outbox), 3)
        self.assertEqual(mail.outbox[2].subject,
                         'Your managed web server has been cancelled')
        self.assertEqual(mail.outbox[2].to, [site.email])
        # Retrieve object
        site = Site.objects.get(pk=site.id)
        self.assertTrue(site.subscription)
        self.assertEqual(site.end_date, today.date())
        self.assertFalse(site.users.exists())

    def test_check_not_cancel_if_paid(self):
        ''' This test checks that if the user does not uploads a PO before 30 days, the site will be cancelled
        automatically'''
        today = datetime.today()
        do_test_login(self, user="test0001")
        # Create site (more than 30 days ago start date)
        site = Site.objects.create(name="testSite", email='amc203@cam.ac.uk',
                                   start_date=today-timedelta(days=40))
        site.users.add(User.objects.get(username="test0001"))

        self.assertFalse(hasattr(site, 'billing'))
        pofile = SimpleUploadedFile("file.pdf", "file_content")
        self.client.post(reverse('billing_management', kwargs={'site_id': site.id}),
                         {'purchase_order_number': 'testOrderNumber', 'group': 'testGroup', 'purchase_order': pofile})
        # Retrieve object
        site = Site.objects.get(pk=site.id)
        self.assertTrue(hasattr(site, 'billing'))

        # Check that the site is not cancelled, it has a PO attached
        self.assertIsNone(site.end_date)
        self.assertIn(User.objects.get(username='test0001'), site.users.all())
        check_subscription()
        self.assertEqual(len(mail.outbox), 0)
        # Retrieve object
        site = Site.objects.get(pk=site.id)
        self.assertIsNone(site.end_date)
        self.assertTrue(site.subscription)
        self.assertTrue(site.users.exists())
