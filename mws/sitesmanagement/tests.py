from datetime import datetime
import os
from django.conf import settings
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test import TestCase
from mwsauth.tests import do_test_login
from models import NetworkConfig, Site
import views
from utils import is_camacuk, get_object_or_None


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
        self.assertContains(response,
                            "                <p class=\"campl-notifications-icon campl-warning-icon\" "
                            "style=\"float:none; margin-bottom: 10px;\">\n                    At this moment we cannot "
                            "process any new request for a new Managed Web Server, please try again later.\n"
                            "                </p>")

        NetworkConfig.objects.create(IPv4='1.1.1.1', IPv6='::1.1.1.1', mws_domain="1.mws.cam.ac.uk")
        response = self.client.get(reverse(views.index))
        self.assertContains(response,
                            "<p><a href=\"%s\" class=\"campl-primary-cta\">Register new site</a></p>" %
                            reverse(views.new))

        site = Site.objects.create(name="testSite", institution_id="testinst", start_date=datetime.today())

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

        site = Site.objects.create(name="testSite", institution_id="testinst", start_date=datetime.today())
        response = self.client.get(reverse(views.show, kwargs={'site_id': site.id}))
        self.assertEqual(response.status_code, 403)  # The User is not in the list of auth users

        site.users.add(User.objects.get(username="test0001"))
        response = self.client.get(reverse(views.show, kwargs={'site_id': site.id}))
        self.assertContains(response, "No Billing, please add one.")

    def test_view_new(self):
        response = self.client.get(reverse(views.new))
        self.assertEqual(response.status_code, 302)  # Not logged in, redirected to login
        self.assertTrue(response.url.endswith(
            '%s?next=%s' % (reverse('raven_login'), reverse(views.new))))

        do_test_login(self, user="test0001")

        response = self.client.get(reverse(views.new))
        self.assertEqual(response.status_code, 302)  # There aren't prealocated network configurations
        self.assertTrue(response.url.endswith(reverse(views.index)))

        NetworkConfig.objects.create(IPv4='1.1.1.1', IPv6='::1.1.1.1', mws_domain="1.mws.cam.ac.uk")

        response = self.client.get(reverse(views.new))
        self.assertContains(response, "Request new site")

        response = self.client.post(reverse(views.new), {'siteform-description': 'Desc',
                                                         'siteform-institution_id': 'UIS',
                                                         'siteform-email': 'amc203@cam.ac.uk'})
        self.assertContains(response, "This field is required.") # Empty name, error

        response = self.client.post(reverse(views.new), {'siteform-name': 'Test Site', 'siteform-description': 'Desc',
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

        self.assertContains(response, "Your email &#39;%s&#39; is still unconfirmed, please click on the link of "
                                      "the sent email" % test_site.email )

    def test_view_edit(self):
        response = self.client.get(reverse(views.edit, kwargs={'site_id': 1}))
        self.assertEqual(response.status_code, 302)  # Not logged in, redirected to login
        self.assertTrue(response.url.endswith(
            '%s?next=%s' % (reverse('raven_login'), reverse(views.edit, kwargs={'site_id': 1}))))

        do_test_login(self, user="test0001")

        response = self.client.get(reverse(views.edit, kwargs={'site_id': 1}))
        self.assertEqual(response.status_code, 404)  # The Site does not exist

        site = Site.objects.create(name="testSite", institution_id="testInst", start_date=datetime.today())
        response = self.client.get(reverse(views.edit, kwargs={'site_id': site.id}))
        self.assertEqual(response.status_code, 403)  # The User is not in the list of auth users

        site.users.add(User.objects.get(username="test0001"))
        response = self.client.get(reverse(views.edit, kwargs={'site_id': site.id}))
        self.assertContains(response, "Change information about your MWS")

        suspension = site.suspend_now(input_reason="test suspension")
        response = self.client.get(reverse(views.edit, kwargs={'site_id': site.id}))
        self.assertEqual(response.status_code, 403)  # The site is suspended

        suspension.active = False
        suspension.save()
        response = self.client.get(reverse(views.edit, kwargs={'site_id': site.id}))
        self.assertContains(response, "Change information about your MWS")

        self.assertNotEqual(site.name, 'testSiteChange')
        self.assertNotEqual(site.description, 'testDescChange')
        self.assertNotEqual(site.institution_id, 'UIS')
        self.assertNotEqual(site.email, 'email@change.test')
        response = self.client.post(reverse(views.edit, kwargs={'site_id': site.id}),
                                    {'name': 'testSiteChange', 'description': 'testDescChange',
                                     'institution_id': 'UIS', 'email': 'email@change.test',})
        self.assertEqual(response.status_code, 302)  # Changes done, redirecting
        self.assertTrue(response.url.endswith(reverse(views.show, kwargs={'site_id': site.id})))
        site_changed = Site.objects.get(pk=site.id)
        self.assertEqual(site_changed.name, 'testSiteChange')
        self.assertEqual(site_changed.description, 'testDescChange')
        self.assertEqual(site_changed.institution_id, 'UIS')
        self.assertEqual(site_changed.email, 'email@change.test')

        response = self.client.get(response.url)
        self.assertContains(response, "Your email &#39;%s&#39; is still unconfirmed, please click on the link of "
                                      "the sent email" % site_changed.email )

    def test_view_billing(self):
        response = self.client.get(reverse(views.billing_management, kwargs={'site_id': 1}))
        self.assertEqual(response.status_code, 302)  # Not logged in, redirected to login
        self.assertTrue(response.url.endswith(
            '%s?next=%s' % (reverse('raven_login'), reverse(views.billing_management, kwargs={'site_id': 1}))))

        do_test_login(self, user="test0001")

        response = self.client.get(reverse(views.billing_management, kwargs={'site_id': 1}))
        self.assertEqual(response.status_code, 404)  # The Site does not exist

        site = Site.objects.create(name="testSite", institution_id="testInst", start_date=datetime.today())
        response = self.client.get(reverse(views.billing_management, kwargs={'site_id': site.id}))
        self.assertEqual(response.status_code, 403)  # The User is not in the list of auth users

        site.users.add(User.objects.get(username="test0001"))
        response = self.client.get(reverse(views.billing_management, kwargs={'site_id': site.id}))
        self.assertContains(response, "Change billing data")
        response = self.client.get(reverse(views.show, kwargs={'site_id': site.id}))
        self.assertContains(response, "No Billing, please add one.")

        suspension = site.suspend_now(input_reason="test suspension")
        response = self.client.get(reverse(views.billing_management, kwargs={'site_id': site.id}))
        self.assertEqual(response.status_code, 403)  # The site is suspended

        suspension.active = False
        suspension.save()
        response = self.client.get(reverse(views.billing_management, kwargs={'site_id': site.id}))
        self.assertContains(response, "Change billing data")

        self.assertFalse(hasattr(site, 'billing'))
        with open(os.path.join(settings.BASE_DIR, 'requirements.txt')) as fp:
            response = self.client.post(reverse(views.billing_management, kwargs={'site_id': site.id}),
                                        {'purchase_order_number': 'testOrderNumber', 'group': 'testGroup',
                                         'purchase_order': fp,})
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
                                         'purchase_order': fp,})
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