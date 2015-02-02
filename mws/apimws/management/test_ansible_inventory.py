import uuid
from django.test import TestCase
from django.core.management.base import CommandError
import json
from StringIO import StringIO
from datetime import datetime
from sitesmanagement.models import (
    ServiceNetworkConfig, Site, VirtualMachine, UnixGroup, Vhost, DomainName, HostNetworkConfig)


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
        netconf = ServiceNetworkConfig.objects.create(
            IPv4='198.51.100.255',
            IPv6='2001:db8:212:8::8c:255',
            IPv4private='192.0.2.255',
            mws_private_domain='mws-08246.mws3.private.example',
            mws_domain="mws-12940.mws3.example")
        hostnetconf = HostNetworkConfig.objects.create(
            IPv6='2001:db8:212:8::8c:254',
            hostname="mws-client1.example")
        self.site = Site.objects.create(name="testSite",
                                        institution_id="testinst",
                                        start_date=datetime.today(),
                                        service_network_configuration=netconf)
        self.vm = VirtualMachine.objects.create(
            name="test_vm", primary=True, status="ready", token=uuid.uuid4(),
            site=self.site, host_network_configuration=hostnetconf)
        self.vhost1 = self.vm.vhosts.create(name="vhost1")
        self.vhost2 = self.vm.vhosts.create(name="vhost2")
        self.dom1 = self.vhost1.domain_names.create(name="foo.example",
                                                    status='accepted')
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
    def test_vars(self):
        s = StringIO()
        Command().handle_noargs(list=True, outfile=s)
        r = json.loads(s.getvalue())
        v = r['_meta']['hostvars'][r['mwsclients'][0]]
        self.assertEqual(v['mws_name'], self.site.name)
