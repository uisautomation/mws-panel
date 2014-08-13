from django.conf import settings
from django.contrib.auth.models import User, Group
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.test import TestCase
from ucamwebauth.tests import create_wls_response
from mwsauth.validators import validate_crsids, validate_groupids


def do_test_login(self, user="user1"):
    with self.settings(UCAMWEBAUTH_CERTS={901: """  -----BEGIN CERTIFICATE-----
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
                                                    -----END CERTIFICATE----- """}):
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

        users = validate_crsids("amc203,jw35")
        self.assertEqual(len(users), 2)
        self.assertEqual(users[0].username, "amc203")
        self.assertIsNotNone(users[0].id)
        self.assertFalse(users[0].has_usable_password())
        self.assertEqual(users[1].username, "jw35")
        self.assertIsNotNone(users[1].id)
        self.assertFalse(users[1].has_usable_password())

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
        self.assertEqual(groups[0].id, 101888)

        groups = validate_groupids("101888,101923")
        self.assertEqual(len(groups), 2)
        self.assertEqual(groups[0].id, 101888)
        self.assertEqual(groups[1].id, 101923)

        groups = validate_groupids("")
        self.assertEqual(len(groups), 0)