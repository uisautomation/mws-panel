from datetime import datetime
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