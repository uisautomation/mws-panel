from django.core.urlresolvers import reverse
from django.test import TestCase
import requests


class MetadataTestCase(TestCase):
    fixtures = ['initial_data.json', 'test_metadata.json']
