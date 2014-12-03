import uuid
from django.test import TestCase
from django.core.management.base import CommandError
import json
from StringIO import StringIO
from datetime import datetime
from sitesmanagement.models import (
    NetworkConfig, Site, VirtualMachine, UnixGroup, Vhost, DomainName)


from .commands.ansible_inventory import Command

class SimpleCommandTests(TestCase):
    def test_options(self):
        with self.assertRaises(CommandError):
            Command().handle_noargs(list=None, host=None)
        with self.assertRaises(CommandError):
            Command().handle_noargs(list=True, host="foo")
    def test_args(self):
        with self.assertRaises(CommandError):
            Command().handle("foo", list=True)
    def test_list_minimal(self):
        s = StringIO()
        Command().handle_noargs(list=True, outfile=s)
        r = json.loads(s.getvalue())
        self.assertTrue('_meta' in r)
        self.assertTrue('hostvars' in r['_meta'])
        self.assertTrue(isinstance(r['_meta']['hostvars'], dict))
        self.assertTrue('mwsclients' in r)
        self.assertTrue(isinstance(r['mwsclients'], list))

class TestsWithData(TestCase):
    def setUp(self):
        netconf = NetworkConfig.objects.create(
            IPv4='198.51.100.255',
            IPv6='2001:db8:212:8::8c:255',
            IPv4private='192.0.2.255',
            mws_private_domain='mws-08246.mws3.private.example',
            mws_domain="mws-12940.mws3.example")
        site = Site.objects.create(name="testSite", institution_id="testinst",
                                   start_date=datetime.today(),
                                   network_configuration=netconf)
        self.vm = VirtualMachine.objects.create(
            name="test_vm", primary=True, status="ready", token=uuid.uuid4(), site=site)
    def test_list(self):
        s = StringIO()
        Command().handle_noargs(list=True, outfile=s)
        r = json.loads(s.getvalue())
        self.assertTrue('_meta' in r)
        self.assertTrue('hostvars' in r['_meta'])
        self.assertTrue(isinstance(r['_meta']['hostvars'], dict))
        self.assertTrue('mwsclients' in r)
        self.assertTrue(isinstance(r['mwsclients'], list))

        self.assertEqual(len(r['mwsclients']), 1)
        self.assertTrue(r['mwsclients'][0] in r['_meta']['hostvars'])
        
