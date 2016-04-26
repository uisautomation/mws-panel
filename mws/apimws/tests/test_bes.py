import json
from django.core.urlresolvers import reverse
from django.test import override_settings, TestCase
from mwsauth.tests import do_test_login
from sitesmanagement.models import Site, VirtualMachine
from sitesmanagement.tests.tests import assign_a_site


@override_settings(CELERY_EAGER_PROPAGATES_EXCEPTIONS=True, CELERY_ALWAYS_EAGER=True, BROKER_BACKEND='memory')
class BesTests(TestCase):
    def setUp(self):
        do_test_login(self, user="test0001")
        assign_a_site(self)

    def test_bes_normal_site(self):
        site = Site.objects.first()
        response = self.client.get(reverse("apimws.bes.bes"))
        json_site = {}
        json_site['id'] = "mwssite-%s" % site.id
        for sitekey in site.keys.all():
            json_site['ssh-public-key-%s' % sitekey.type.lower()] = sitekey.public_key
        json_vms = []
        for vm in VirtualMachine.objects.filter(service__site = site):
            json_vm = {}
            json_vm['name'] = vm.name
            json_vm['disabled'] = vm.service.site.disabled
            json_vm['fqdn'] = vm.network_configuration.name
            json_vm['service_fqdn'] = vm.service.network_configuration.name
            json_vm['location'] = 'mws-cluster-1'
            json_vm['backup'] = ['/replicated']
            json_vm['backup-user'] = "dump"
            json_vms.append(json_vm)
        json_site['vms'] = json_vms
        self.assertContains(response, json.dumps([json_site]))
