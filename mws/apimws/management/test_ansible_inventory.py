import uuid
from django.test import TestCase
from django.core.management.base import CommandError
import json
from StringIO import StringIO
from datetime import datetime
from apimws.models import Cluster, Host
from apimws.xen import which_cluster
from sitesmanagement.models import (Site, VirtualMachine, NetworkConfig, Service, ServerType)
from .commands.ansible_inventory import Command


class SimpleCommandTests(TestCase):

    def test_options(self):
        with self.assertRaises(CommandError):
            Command().handle(list=None, host=None)
        with self.assertRaises(CommandError):
            Command().handle(list=True, host="foo")

    def test_list_minimal(self):
        s = StringIO()
        Command().handle(list=True, outfile=s)
        r = json.loads(s.getvalue())
        self.assertTrue('_meta' in r)
        self.assertTrue('hostvars' in r['_meta'])
        self.assertTrue(isinstance(r['_meta']['hostvars'], dict))
        self.assertTrue('mwsclients' in r)
        self.assertTrue(isinstance(r['mwsclients'], list))


class TestsWithData(TestCase):

    def setUp(self):
        cluster = Cluster.objects.create(name="mws-test-1")
        Host.objects.create(hostname="mws-test-1.dev.mws3.cam.ac.uk", cluster=cluster)
        NetworkConfig.objects.create(IPv4='198.51.100.255', IPv6='2001:db8:212:8::8c:255', type='ipvxpub',
                                     name="mws-12940.mws3.example")
        NetworkConfig.objects.create(IPv4='192.0.2.255', type='ipv4priv',
                                     name='mws-08246.mws3.private.example')
        NetworkConfig.objects.create(IPv6='2001:db8:212:8::8c:254', name='mws-client1.example', type='ipv6')
        self.site = Site.objects.create(name="testSite", start_date=datetime.today(), type=ServerType.objects.get(id=1))
        self.service = Service.objects.create(type="production", site=self.site, status="ready",
                                              network_configuration=NetworkConfig.get_free_prod_service_config())
        self.vm = VirtualMachine.objects.create(
            name="test_vm", token=uuid.uuid4(), service=self.service,
            network_configuration=NetworkConfig.get_free_host_config(), cluster=which_cluster())
        self.vhost1 = self.service.vhosts.create(name="vhost1")
        self.vhost2 = self.service.vhosts.create(name="vhost2")
        self.dom1 = self.vhost1.domain_names.create(name="foo.example", status='external')

    def test_list(self):
        s = StringIO()
        Command().handle(list=True, outfile=s)
        r = json.loads(s.getvalue())
        self.assertTrue('_meta' in r)
        self.assertTrue('hostvars' in r['_meta'])
        self.assertTrue(isinstance(r['_meta']['hostvars'], dict))
        self.assertTrue('mwsclients' in r)
        self.assertTrue(isinstance(r['mwsclients'], list))

        self.assertEqual(len(r['mwsclients']), 1)
        self.assertTrue(r['mwsclients'][0] in r['_meta']['hostvars'])

    def test_status(self):
        # Make sure that unusual statuses have the right consequences
        s = StringIO()
        self.service.status = "ansible_queued"
        self.service.save()
        Command().handle(list=True, outfile=s)
        r = json.loads(s.getvalue())
        self.assertEqual(len(r['mwsclients']), 1)

    def test_vars(self):
        s = StringIO()
        Command().handle(list=True, outfile=s)
        r = json.loads(s.getvalue())
        v = r['_meta']['hostvars'][r['mwsclients'][0]]
        # Make sure that SSH target is some kind of a name for the host.
        self.assertNotEqual(v['ansible_ssh_host'], None)
        self.assertIn(v['ansible_ssh_host'], (
            self.vm.network_configuration.IPv4,
            self.vm.network_configuration.IPv6,
            self.vm.network_configuration.name))

        self.assertEqual(v['mws_name'], self.site.name)
        self.assertEqual(v['mws_service_ipv4'], self.service.network_configuration.IPv4)
        self.assertEqual(v['mws_service_ipv6'], self.service.network_configuration.IPv6)
        if self.vm.network_configuration.IPv4:
            self.assertEqual(v['mws_ipv4'], self.vm.network_configuration.IPv4)
        self.assertEqual(v['mws_ipv6'], self.vm.network_configuration.IPv6)
        self.assertEqual(v['mws_service_fqdn'], self.vm.service.network_configuration.name)
