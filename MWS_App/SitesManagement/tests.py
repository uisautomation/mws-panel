from django.core.urlresolvers import reverse
from django.test import TestCase
import requests


class MetadataTestCase(TestCase):
    fixtures = ['initial_data.json', 'test_metadata.json']

    def login(self):
        self.client.get(reverse('raven_return') + '?' +
                        requests.post('https://demo.raven.cam.ac.uk/auth/authenticate2.html',
                                      {'url': 'http://localhost:8000/raven_return/',
                                       'userid': 'test0001', 'pwd': 'test',
                                       'ver': '3'}).history[1].url.split('?')[1])

    def test_raven_protocol(self):
        self.login()
        self.assertIn('_auth_user_id', self.client.session)