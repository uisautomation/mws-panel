from datetime import datetime
from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.test import TestCase
from ucamwebauth.tests import create_wls_response
from mwsauth import views
from mwsauth.utils import get_or_create_user_by_crsid, get_or_create_group_by_groupid
from ucamlookup import user_in_groups
from mwsauth.validators import validate_crsids, validate_groupids
from sitesmanagement.models import Site, Suspension, VirtualMachine, NetworkConfig
from ucamlookup.models import LookupGroup


def do_test_login(self, user="user1"):
    with self.settings(UCAMWEBAUTH_CERTS={901: """-----BEGIN CERTIFICATE-----
MIIDzTCCAzagAwIBAgIBADANBgkqhkiG9w0BAQQFADCBpjELMAkGA1UEBhMCR0Ix
EDAOBgNVBAgTB0VuZ2xhbmQxEjAQBgNVBAcTCUNhbWJyaWRnZTEgMB4GA1UEChMX
VW5pdmVyc2l0eSBvZiBDYW1icmlkZ2UxLTArBgNVBAsTJENvbXB1dGluZyBTZXJ2
aWNlIERFTU8gUmF2ZW4gU2VydmljZTEgMB4GA1UEAxMXUmF2ZW4gREVNTyBwdWJs
aWMga2V5IDEwHhcNMDUwNzI2MTMyMTIwWhcNMDUwODI1MTMyMTIwWjCBpjELMAkG
A1UEBhMCR0IxEDAOBgNVBAgTB0VuZ2xhbmQxEjAQBgNVBAcTCUNhbWJyaWRnZTEg
MB4GA1UEChMXVW5pdmVyc2l0eSBvZiBDYW1icmlkZ2UxLTArBgNVBAsTJENvbXB1
dGluZyBTZXJ2aWNlIERFTU8gUmF2ZW4gU2VydmljZTEgMB4GA1UEAxMXUmF2ZW4g
REVNTyBwdWJsaWMga2V5IDEwgZ8wDQYJKoZIhvcNAQEBBQADgY0AMIGJAoGBALhF
i9tIZvjYQQRfOzP3cy5ujR91ZntQnQehldByHlchHRmXwA1ot/e1WlHPgIjYkFRW
lSNcSDM5r7BkFu69zM66IHcF80NIopBp+3FYqi5uglEDlpzFrd+vYllzw7lBzUnp
CrwTxyO5JBaWnFMZrQkSdspXv89VQUO4V4QjXV7/AgMBAAGjggEHMIIBAzAdBgNV
HQ4EFgQUgjC6WtA4jFf54kxlidhFi8w+0HkwgdMGA1UdIwSByzCByIAUgjC6WtA4
jFf54kxlidhFi8w+0HmhgaykgakwgaYxCzAJBgNVBAYTAkdCMRAwDgYDVQQIEwdF
bmdsYW5kMRIwEAYDVQQHEwlDYW1icmlkZ2UxIDAeBgNVBAoTF1VuaXZlcnNpdHkg
b2YgQ2FtYnJpZGdlMS0wKwYDVQQLEyRDb21wdXRpbmcgU2VydmljZSBERU1PIFJh
dmVuIFNlcnZpY2UxIDAeBgNVBAMTF1JhdmVuIERFTU8gcHVibGljIGtleSAxggEA
MAwGA1UdEwQFMAMBAf8wDQYJKoZIhvcNAQEEBQADgYEAsdyB+9szctHHIHE+S2Kg
LSxbGuFG9yfPFIqaSntlYMxKKB5ba/tIAMzyAOHxdEM5hi1DXRsOok3ElWjOw9oN
6Psvk/hLUN+YfC1saaUs3oh+OTfD7I4gRTbXPgsd6JgJQ0TQtuGygJdaht9cRBHW
wOq24EIbX5LquL9w+uvnfXw=
-----END CERTIFICATE-----"""}):
        self.client.get(reverse('raven_return'),
                        {'WLS-Response': create_wls_response(
                            raven_url=settings.UCAMWEBAUTH_RETURN_URL,
                            raven_principal=user)})
        self.assertIn('_auth_user_id', self.client.session)


class AuthTestCases(TestCase):

    def test_validate_crisd(self):
        with self.assertRaises(ValidationError):
            validate_crsids("wrongwrongwrong")

        users = validate_crsids("amc203")
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0].username, "amc203")
        self.assertIsNotNone(users[0].id)
        self.assertFalse(users[0].has_usable_password())
        self.assertIsNot(users[0].last_name, "")
        self.assertIsNot(users[0].last_name, None)

        users = validate_crsids("amc203,jw35")
        self.assertEqual(len(users), 2)
        self.assertEqual(users[0].username, "amc203")
        self.assertIsNotNone(users[0].id)
        self.assertFalse(users[0].has_usable_password())
        self.assertIsNot(users[0].last_name, "")
        self.assertIsNot(users[0].last_name, None)
        self.assertEqual(users[1].username, "jw35")
        self.assertIsNotNone(users[1].id)
        self.assertFalse(users[1].has_usable_password())
        self.assertIsNot(users[1].last_name, "")
        self.assertIsNot(users[1].last_name, None)

        with self.assertRaises(User.DoesNotExist):
            User.objects.get(username="wrongwrongwrong")

        users = validate_crsids("")
        self.assertEqual(len(users), 0)

    def test_validate_groups(self):
        with self.assertRaises(ValidationError):
            validate_groupids("wrongwrongwrong")

        with self.assertRaises(ValidationError):
            validate_groupids("123456")

        groups = validate_groupids("101888")
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].lookup_id, "101888")
        self.assertIsNot(groups[0].name, "")
        self.assertIsNot(groups[0].name, None)

        groups = validate_groupids("101888,101923")
        self.assertEqual(len(groups), 2)
        self.assertEqual(groups[0].lookup_id, "101888")
        self.assertIsNot(groups[0].name, "")
        self.assertIsNot(groups[0].name, None)
        self.assertEqual(groups[1].lookup_id, "101923")
        self.assertIsNot(groups[1].name, "")
        self.assertIsNot(groups[1].name, None)

        groups = validate_groupids("")
        self.assertEqual(len(groups), 0)

    def test_get_or_create_user_or_group(self):
        with self.assertRaises(User.DoesNotExist):
            User.objects.get(username="amc203")
        user1 = get_or_create_user_by_crsid("amc203")
        user2 = User.objects.get(username="amc203")
        self.assertEqual(user1.id, user2.id)

        with self.assertRaises(LookupGroup.DoesNotExist):
            LookupGroup.objects.get(lookup_id="101888")
        group1 = get_or_create_group_by_groupid(101888)
        group2 = LookupGroup.objects.get(lookup_id="101888")
        self.assertEqual(group1.lookup_id, group2.lookup_id)

    def test_user_in_groups(self):
        amc203 = get_or_create_user_by_crsid("amc203")
        information_systems_group = get_or_create_group_by_groupid(101888)
        self.assertTrue(user_in_groups(amc203, [information_systems_group]))
        finance_group = get_or_create_group_by_groupid(101923)
        self.assertFalse(user_in_groups(amc203, [finance_group]))

    def test_auth_change(self):
        response = self.client.get(reverse(views.auth_change, kwargs={'site_id': 1}))
        self.assertEqual(response.status_code, 302)  # Not logged in, redirected to login
        self.assertTrue(response.url.endswith(
            '%s?next=%s' % (reverse('raven_login'), reverse(views.auth_change, kwargs={'site_id': 1}))))

        do_test_login(self, user="amc203")
        amc203_user = User.objects.get(username="amc203")

        response = self.client.get(reverse(views.auth_change, kwargs={'site_id': 1}))
        self.assertEqual(response.status_code, 404)  # Site does not exists

        site_without_auth_users = Site.objects.create(name="test_site1", start_date=datetime.today())
        VirtualMachine.objects.create(primary=True, status='requested', site=site_without_auth_users,
                                      network_configuration=NetworkConfig.objects.create(IPv4="1.1.1.1",
                                                                                         IPv6="::ffff:1.1.1.1",
                                                                                         mws_domain="1.mws.cam.ac.uk"))

        response = self.client.get(reverse(views.auth_change, kwargs={'site_id': site_without_auth_users.id}))
        self.assertEqual(response.status_code, 403)  # User is not authorised

        site_without_auth_users.users.add(amc203_user)
        site_with_auth_users = site_without_auth_users

        response = self.client.get(reverse(views.auth_change, kwargs={'site_id': site_with_auth_users.id}))
        self.assertContains(response, "amc203", status_code=200)  # User is authorised

        site_with_auth_groups = Site.objects.create(name="test_site2", start_date=datetime.today())
        information_systems_group = get_or_create_group_by_groupid(101888)
        site_with_auth_groups.groups.add(information_systems_group)
        VirtualMachine.objects.create(primary=True, status='requested', site=site_with_auth_groups,
                                      network_configuration=NetworkConfig.objects.create(IPv4="1.1.1.2",
                                                                                         IPv6="::ffff:1.1.1.2",
                                                                                         mws_domain="2.mws.cam.ac.uk"))

        response = self.client.get(reverse(views.auth_change, kwargs={'site_id': site_with_auth_groups.id}))
        self.assertContains(response, "101888", status_code=200)  # User is in an authorised group
        self.assertNotContains(response, "amc203", status_code=200)

        suspension = Suspension.objects.create(reason="test_suspension", site=site_with_auth_users,
                                               start_date=datetime.today())
        response = self.client.get(reverse(views.auth_change, kwargs={'site_id': site_with_auth_users.id}))
        self.assertEqual(response.status_code, 302)  # Site is suspended
        self.assertTrue(response.url.endswith(
            '%s' % reverse('sitesmanagement.views.show', kwargs={'site_id': site_with_auth_users.id})))
        self.assertEqual(self.client.get(response.url).status_code, 403)  # Site is suspended
        suspension.delete()

        self.assertEqual(len(site_with_auth_users.users.all()), 1)
        self.assertEqual(site_with_auth_users.users.first(), amc203_user)
        self.assertEqual(len(site_with_auth_users.groups.all()), 0)
        response = self.client.post(reverse(views.auth_change, kwargs={'site_id': site_with_auth_users.id}), {
            'crsids': "amc203",
            'groupids': "101888"
            # we authorise amc203 user and 101888 group
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith(
            '%s' % reverse('sitesmanagement.views.show', kwargs={'site_id': site_with_auth_users.id})))
        self.assertEqual(self.client.get(response.url).status_code, 200)
        self.assertEqual(len(site_with_auth_users.users.all()), 1)
        self.assertEqual(site_with_auth_users.users.first(), amc203_user)
        self.assertEqual(len(site_with_auth_users.groups.all()), 1)
        self.assertEqual(site_with_auth_users.groups.first(), information_systems_group)

        response = self.client.post(reverse(views.auth_change, kwargs={'site_id': site_with_auth_users.id}), {
            # we remove all users and groups authorised, we do not send any crsids or groupids
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith(
            '%s' % reverse('sitesmanagement.views.show', kwargs={'site_id': site_with_auth_users.id})))
        self.assertEqual(self.client.get(response.url).status_code, 403)  # User is no longer authorised
        self.assertEqual(len(site_with_auth_users.users.all()), 0)
        self.assertEqual(len(site_with_auth_users.groups.all()), 0)

        self.assertEqual(len(site_with_auth_groups.users.all()), 0)
        self.assertEqual(len(site_with_auth_groups.groups.all()), 1)
        self.assertEqual(site_with_auth_groups.groups.first(), information_systems_group)
        response = self.client.post(reverse(views.auth_change, kwargs={'site_id': site_with_auth_groups.id}), {
            'crsids': "amc203",
            'groupids': "101888"
            # we authorise amc203 user and 101888 group
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith(
            '%s' % reverse('sitesmanagement.views.show', kwargs={'site_id': site_with_auth_groups.id})))
        self.assertEqual(self.client.get(response.url).status_code, 200)
        self.assertEqual(len(site_with_auth_groups.users.all()), 1)
        self.assertEqual(site_with_auth_groups.users.first(), amc203_user)
        self.assertEqual(len(site_with_auth_groups.groups.all()), 1)
        self.assertEqual(site_with_auth_groups.groups.first(), information_systems_group)

        response = self.client.post(reverse(views.auth_change, kwargs={'site_id': site_with_auth_groups.id}), {
            # we remove all users and groups authorised, we do not send any crsids or groupids
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith(
            '%s' % reverse('sitesmanagement.views.show', kwargs={'site_id': site_with_auth_groups.id})))
        self.assertEqual(self.client.get(response.url).status_code, 403)  # User is no longer authorised
        self.assertEqual(len(site_with_auth_groups.users.all()), 0)
        self.assertEqual(len(site_with_auth_groups.groups.all()), 0)

        site_with_auth_users.users.add(amc203_user)
