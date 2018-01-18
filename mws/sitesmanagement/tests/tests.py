import uuid
import mock
import os
from datetime import datetime
from django.conf import settings
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test import TestCase, override_settings
from apimws.models import Cluster, Host, AnsibleConfiguration
from apimws.utils import preallocate_new_site
from apimws.views import post_installation
from apimws.xen import which_cluster
from mwsauth.tests import do_test_login
import sitesmanagement.views as views
from sitesmanagement.models import Site, VirtualMachine, UnixGroup, Vhost, DomainName, NetworkConfig, Service, \
    ServerType
from sitesmanagement.utils import is_camacuk, get_object_or_None


def pre_create_site():
    NetworkConfig.objects.create(IPv4='131.111.58.253', IPv6='2001:630:212:8::8c:253', type='ipvxpub',
                                               name="mws-66424.mws3.csx.cam.ac.uk")
    NetworkConfig.objects.create(IPv4='172.28.18.253', type='ipv4priv',
                                 name='mws-46250.mws3.csx.private.cam.ac.uk')
    NetworkConfig.objects.create(IPv6='2001:630:212:8::8c:ff4', name='mws-client1', type='ipv6')
    NetworkConfig.objects.create(IPv6='2001:630:212:8::8c:ff3', name='mws-client2', type='ipv6')
    NetworkConfig.objects.create(IPv4='131.111.58.252', IPv6='2001:630:212:8::8c:252', type='ipvxpub',
                                               name="mws-66423.mws3.csx.cam.ac.uk")
    NetworkConfig.objects.create(IPv4='172.28.18.252', type='ipv4priv',
                                 name='mws-46251.mws3.csx.private.cam.ac.uk')
    NetworkConfig.objects.create(IPv6='2001:630:212:8::8c:ff2', name='mws-client3', type='ipv6')
    NetworkConfig.objects.create(IPv6='2001:630:212:8::8c:ff1', name='mws-client4', type='ipv6')

    with mock.patch("apimws.xen.subprocess") as mock_subprocess:
        def fake_subprocess_output(*args, **kwargs):
            if (set(args[0]) & set(['vmmanager', 'create'])) == set(['vmmanager', 'create']):
                return '{"vmid": "mws-client1"}'
            elif (set(args[0]) & set(["ssh-keygen", "-lf"])) == set(["ssh-keygen", "-lf"]):
                return '2048 fa:ee:51:a2:3f:95:71:6a:2f:8c:e1:66:df:be:f1:2a id_rsa.pub (RSA)'
            elif (set(args[0]) & set(["ssh-keygen", "-r", "replacehostname", "-f"])) == \
                    set(["ssh-keygen", "-r", "replacehostname", "-f"]):
                return "replacehostname IN SSHFP 1 1 9ddc245c6cf86667e33fe3186b7226e9262eac16\n" \
                       "replacehostname IN SSHFP 1 2 " \
                       "2f27ce76295fdffb576d714fea586dd0a87a5a2ffa621b4064e225e36c8cf83c\n"
        mock_subprocess.check_output.side_effect = fake_subprocess_output
        mock_subprocess.Popen().communicate.return_value = (
            '{"pubkey": "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQClBKpj+/WXlxJMY2iYw1mB1qYLM8YDjFS6qSiT6UmNLLhXJ' \
            'BEfd6vOMErM1IfDsYN+W3604hukxwC859TU4ZLQYD6wFI2D+qMhb2UTcoLlOYD7TG436RXKbxK4iAT7ll3XUT8VxZUq/AZKVs' \
            'vmH309l5LcW6UPO0PVYoafpo4+Fmv5c/CRTvp5X0eaoXtgT49h58/GwNlD2RrVPInjI9isa8/k8qiNaWEHYOGKC343BQIR9Sx' \
            '+5HQ16wf3x3fUFeMTOYfsbvwQ9T5pkKpFoiUYRxjsz7bXdPQPT4A1UrfgmGnTLJGSUh+uvHYLe7izWoMCCDCV0+Zyn0Ilrlfm' \
            'N+cD"}', '')

        # We create a new server that will be used in the preallocation list
        preallocate_new_site()

    # We simulate the VM finishing installing
    vm = VirtualMachine.objects.first()
    with mock.patch("apimws.ansible.subprocess") as mock_subprocess:
        with mock.patch("apimws.vm.change_vm_power_state") as mock_change_vm_power_state:
            mock_subprocess.check_output.return_value.returncode = 0
            mock_change_vm_power_state.return_value = True
            mock_change_vm_power_state.delay.return_value = True
            mock_request = mock.Mock()
            mock_request.method = 'POST'
            mock_request.POST = {'vm': vm.id, 'token': vm.token}
            post_installation(mock_request)


def assign_a_site(test_interface, pre_create=True):
    if pre_create:
        pre_create_site()
    response = test_interface.client.get(reverse('listsites'))
    test_interface.assertInHTML("<p><a href=\"%s\" class=\"campl-primary-cta\">Register new server</a></p>" %
                                reverse('newsite'), response.content)
    with mock.patch("apimws.xen.subprocess") as mock_subprocess:
        def fake_subprocess_output(*args, **kwargs):
            if (set(args[0]) & set(['vmmanager', 'create'])) == set(['vmmanager', 'create']):
                return '{"vmid": "mws-client1"}'
            elif (set(args[0]) & set(["ssh-keygen", "-lf"])) == set(["ssh-keygen", "-lf"]):
                return '2048 fa:ee:51:a2:3f:95:71:6a:2f:8c:e1:66:df:be:f1:2a id_rsa.pub (RSA)'
            elif (set(args[0]) & set(["ssh-keygen", "-r", "replacehostname", "-f"])) == \
                    set(["ssh-keygen", "-r", "replacehostname", "-f"]):
                return "replacehostname IN SSHFP 1 1 9ddc245c6cf86667e33fe3186b7226e9262eac16\n" \
                       "replacehostname IN SSHFP 1 2 " \
                       "2f27ce76295fdffb576d714fea586dd0a87a5a2ffa621b4064e225e36c8cf83c\n"
        mock_subprocess.check_output.side_effect = fake_subprocess_output
        mock_subprocess.Popen().communicate.return_value = (
            '{"pubkey": "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQClBKpj+/WXlxJMY2iYw1mB1qYLM8YDjFS6qSiT6UmNLLhXJ' \
            'BEfd6vOMErM1IfDsYN+W3604hukxwC859TU4ZLQYD6wFI2D+qMhb2UTcoLlOYD7TG436RXKbxK4iAT7ll3XUT8VxZUq/AZKVs' \
            'vmH309l5LcW6UPO0PVYoafpo4+Fmv5c/CRTvp5X0eaoXtgT49h58/GwNlD2RrVPInjI9isa8/k8qiNaWEHYOGKC343BQIR9Sx' \
            '+5HQ16wf3x3fUFeMTOYfsbvwQ9T5pkKpFoiUYRxjsz7bXdPQPT4A1UrfgmGnTLJGSUh+uvHYLe7izWoMCCDCV0+Zyn0Ilrlfm' \
            'N+cD"}', '')
        with mock.patch("apimws.xen.change_vm_power_state") as mock_subprocess2:
            def fake_output_api(*args, **kwargs):
                return True
            mock_subprocess2.side_effect = fake_output_api

            with mock.patch("apimws.ansible.subprocess") as mock_subprocess:
                with mock.patch("apimws.vm.change_vm_power_state") as mock_change_vm_power_state:
                    mock_subprocess.check_output.return_value.returncode = 0
                    mock_change_vm_power_state.return_value = True
                    mock_change_vm_power_state.delay.return_value = True
                    response = test_interface.client.post(reverse('newsite'), {'siteform-name': 'Test Site',
                                                                               'siteform-description': 'Desc',
                                                                               'siteform-email': 'amc203@cam.ac.uk',
                                                                               'siteform-type': 1})
                    test_interface.assertIn(response.status_code, [200, 302])
                # TODO create the checks of how the mock was called
                # mock_subprocess.check_output.assert_called_with(["userv", "mws-admin", "mws_xen_vm_api",
                #                                                  settings.VM_END_POINT[0],
                #                                                  "create",
                #                                                  "{}"])

    site = Site.objects.last()
    test_interface.assertEqual(site.name, 'Test Site')
    test_interface.assertEqual(site.email, 'amc203@cam.ac.uk')
    test_interface.assertEqual(site.description, 'Desc')
    return site


@override_settings(CELERY_EAGER_PROPAGATES_EXCEPTIONS=True, CELERY_ALWAYS_EAGER=True, BROKER_BACKEND='memory')
class SiteManagementTests(TestCase):
    fixtures = [os.path.join(settings.BASE_DIR, 'sitesmanagement/fixtures/network_configuration_dev.yaml'), ]

    def test_is_camacuk_helper(self):
        self.assertTrue(is_camacuk("www.cam.ac.uk"))
        self.assertFalse(is_camacuk("www.com.ac.uk"))

    def test_get_object_or_none(self):
        self.assertIsNone(get_object_or_None(User, username="test0001"))
        User.objects.create_user(username="test0001")
        self.assertIsNotNone(get_object_or_None(User, username="test0001"))

    def test_view_index(self):
        response = self.client.get(reverse('listsites'))
        self.assertEqual(response.status_code, 302)  # Not logged in, redirected to login
        self.assertTrue(response.url.endswith(
            '%s?next=%s' % (reverse('raven_login'), reverse('listsites'))))

        do_test_login(self, user="test0001")

        response = self.client.get(reverse('listsites'))
        self.assertInHTML("<p class=\"campl-notifications-icon campl-warning-icon\" style=\"float:none; margin-bottom: "
                          "10px;\">At this moment we cannot process any new requests for the Managed Web Service, "
                          "please try again later.</p>", response.content)

        site = assign_a_site(self)
        response = self.client.get(reverse('listsites'))
        self.assertContains(response, site.name)

    def test_view_show(self):
        response = self.client.get(reverse('showsite', kwargs={'site_id': 1}))
        self.assertEqual(response.status_code, 302)  # Not logged in, redirected to login
        self.assertTrue(response.url.endswith(
            '%s?next=%s' % (reverse('raven_login'), reverse('showsite', kwargs={'site_id': 1}))))

        do_test_login(self, user="test0001")

        response = self.client.get(reverse('showsite', kwargs={'site_id': 1}))
        self.assertEqual(response.status_code, 404)  # The Site does not exist

        NetworkConfig.objects.create(IPv4='131.111.58.253', IPv6='2001:630:212:8::8c:253', type='ipvxpub',
                                     name="mws-66424.mws3.csx.cam.ac.uk")

        NetworkConfig.objects.create(IPv4='172.28.18.253', type='ipv4priv',
                                     name='mws-46250.mws3.csx.private.cam.ac.uk')

        NetworkConfig.objects.create(IPv6='2001:630:212:8::8c:ff4', name='mws-client1', type='ipv6')

        site = Site.objects.create(name="testSite", start_date=datetime.today(), type=ServerType.objects.get(id=1))

        service = Service.objects.create(network_configuration=NetworkConfig.get_free_prod_service_config(), site=site,
                                         type='production', status='requested')

        Vhost.objects.create(name="default", service=service)

        response = self.client.get(site.get_absolute_url())
        self.assertEqual(response.status_code, 403)  # The User is not in the list of auth users

        site.users.add(User.objects.get(username="test0001"))
        response = self.client.get(site.get_absolute_url())
        self.assertContains(response, "No billing details are available")

    def test_view_new(self):
        response = self.client.get(reverse('newsite'))
        self.assertEqual(response.status_code, 302)  # Not logged in, redirected to login
        self.assertTrue(response.url.endswith(
            '%s?next=%s' % (reverse('raven_login'), reverse('newsite'))))

        do_test_login(self, user="test0001")

        response = self.client.get(reverse('newsite'))
        self.assertRedirects(response, expected_url=reverse('listsites'))

        pre_create_site()

        response = self.client.get(reverse('newsite'))
        self.assertContains(response, "Request new server")

        response = self.client.post(reverse('newsite'), {'siteform-description': 'Desc',
                                                         'siteform-email': 'amc203@cam.ac.uk'})
        self.assertContains(response, "This field is required.")  # Empty name, error

        test_site = assign_a_site(self, pre_create=False)

        # TODO test email check
        # TODO test dns api
        # TODO test errors

        response = self.client.get(test_site.get_absolute_url())

        self.assertContains(response, "Your email %s is unconfirmed, please check your email inbox and "
                                      "click on the link of the email we have sent you." % test_site.email)

        self.assertEqual(len(test_site.production_vms), 1)

        # Disable site
        self.assertFalse(test_site.disabled)
        with mock.patch("apimws.vm.change_vm_power_state") as mock_change_vm_power_state:
            mock_change_vm_power_state.return_value = True
            mock_change_vm_power_state.delay.return_value = True
            self.client.post(reverse('disablesite', kwargs={'site_id': test_site.id}))
        # TODO test that views are restricted
        self.assertTrue(Site.objects.get(pk=test_site.id).disabled)
        # Enable site
        with mock.patch("apimws.ansible.subprocess") as mock_subprocess:
            with mock.patch("apimws.vm.change_vm_power_state") as mock_change_vm_power_state:
                mock_subprocess.check_output.return_value.returncode = 0
                mock_change_vm_power_state.return_value = True
                mock_change_vm_power_state.delay.return_value = True
                self.client.post(reverse('enablesite', kwargs={'site_id': test_site.id}))
        # TODO test that views are no longer restricted
        self.assertFalse(Site.objects.get(pk=test_site.id).disabled)

        self.assertEqual(len(test_site.test_vms), 0)

        # TODO Clone first VM into the secondary VM
        # self.client.post(reverse(views.clone_vm_view, kwargs={'site_id': test_site.id}), {'primary_vm': 'true'})
        #
        # self.assertEqual(len(test_site.test_vms), 1)
        #
        # self.client.delete(reverse(views.delete_vm, kwargs={'service_id': test_site.secondary_vm.service.id}))

        with mock.patch("apimws.vm.change_vm_power_state") as mock_vm_api:
            mock_vm_api.return_value = True
            mock_vm_api.delay.return_value = True
            self.client.post(reverse('deletesite', kwargs={'site_id': test_site.id}))
        self.assertIsNone(Site.objects.get(pk=test_site.id).end_date)

        with mock.patch("apimws.vm.change_vm_power_state") as mock_vm_api:
            mock_vm_api.return_value = True
            mock_vm_api.delay.return_value = True
            self.client.post(reverse('deletesite', kwargs={'site_id': test_site.id}), {'confirmation': 'yes'})
        self.assertIsNotNone(Site.objects.get(pk=test_site.id).end_date)

        # TODO test delete

    def test_view_edit(self):
        response = self.client.get(reverse('editsite', kwargs={'site_id': 1}))
        self.assertEqual(response.status_code, 302)  # Not logged in, redirected to login
        self.assertTrue(response.url.endswith(
            '%s?next=%s' % (reverse('raven_login'), reverse('editsite', kwargs={'site_id': 1}))))

        do_test_login(self, user="test0001")

        response = self.client.get(reverse('editsite', kwargs={'site_id': 1}))
        self.assertEqual(response.status_code, 404)  # The Site does not exist

        site = assign_a_site(self)

        response = self.client.get(reverse('editsite', kwargs={'site_id': site.id}))
        self.assertContains(response, "Managed Web Service account settings")

        response = self.client.get(reverse('editsite', kwargs={'site_id': site.id}))
        self.assertContains(response, "Managed Web Service account settings")

        self.assertNotEqual(site.name, 'testSiteChange')
        self.assertNotEqual(site.description, 'testDescChange')
        self.assertNotEqual(site.email, 'email@change.test')
        response = self.client.post(reverse('editsite', kwargs={'site_id': site.id}),
                                    {'name': 'testSiteChange', 'description': 'testDescChange',
                                     'email': 'email@change.test'})
        self.assertRedirects(response, expected_url=site.get_absolute_url())  # Changes done, redirecting

        site_changed = Site.objects.get(pk=site.id)
        self.assertEqual(site_changed.name, 'testSiteChange')
        self.assertEqual(site_changed.description, 'testDescChange')
        self.assertEqual(site_changed.email, 'email@change.test')

        response = self.client.post(reverse('editsite', kwargs={'site_id': site.id}),
                                    {'name': 'testSiteChange', 'description': 'testDescChange',
                                     'email': 'emailchangetest'})
        self.assertContains(response, '<ul class="errorlist"><li>Enter a valid email address.</li></ul>')
        site_changed = Site.objects.get(pk=site.id)  # Refresh site from DB
        self.assertEqual(site_changed.email, 'email@change.test')

        response = self.client.get(reverse('showsite', kwargs={'site_id': site_changed.id}))
        self.assertContains(response, "Your email %s is unconfirmed, please check your email inbox and click "
                                      "on the link of the email we have sent you." % site_changed.email)

        site_changed.users.remove(User.objects.get(username="test0001"))
        response = self.client.get(reverse('editsite', kwargs={'site_id': site_changed.id}))
        self.assertEqual(response.status_code, 403)  # The User is not in the list of auth users

        site_changed.users.add(User.objects.get(username="test0001"))

        with mock.patch("apimws.vm.change_vm_power_state") as mock_change_vm_power_state:
            mock_change_vm_power_state.return_value = True
            mock_change_vm_power_state.delay.return_value = True
            site.disable()
        site.suspend_now(input_reason="test suspension")
        response = self.client.get(reverse('editsite', kwargs={'site_id': site.id}))
        self.assertEqual(response.status_code, 403)  # The site is suspended


@override_settings(CELERY_EAGER_PROPAGATES_EXCEPTIONS=True, CELERY_ALWAYS_EAGER=True, BROKER_BACKEND='memory')
class SiteManagement2Tests(TestCase):
    def setUp(self):
        do_test_login(self, user="test0001")
        NetworkConfig.objects.create(IPv4='131.111.58.253', IPv6='2001:630:212:8::8c:253', type='ipvxpub',
                                     name="mws-66424.mws3.csx.cam.ac.uk")
        NetworkConfig.objects.create(IPv4='172.28.18.253', type='ipv4priv',
                                     name='mws-46250.mws3.csx.private.cam.ac.uk')
        NetworkConfig.objects.create(IPv6='2001:630:212:8::8c:ff4', name='mws-client1', type='ipv6')
        NetworkConfig.objects.create(IPv6='2001:630:212:8::8c:ff3', name='mws-client2', type='ipv6')
        NetworkConfig.objects.create(IPv6='2001:630:212:8::8c:ff2', name='mws-client3', type='ipv6')
        NetworkConfig.objects.create(IPv6='2001:630:212:8::8c:ff1', name='mws-client4', type='ipv6')

    def create_site(self):
        cluster = Cluster.objects.create(name="mws-test-1")
        Host.objects.create(hostname="mws-test-1.dev.mws3.cam.ac.uk", cluster=cluster)
        site = Site.objects.create(name="testSite", start_date=datetime.today(), type=ServerType.objects.get(id=1))
        site.users.add(User.objects.get(username='test0001'))
        service = Service.objects.create(site=site, type='production', status="ready",
                                         network_configuration=NetworkConfig.get_free_prod_service_config())
        VirtualMachine.objects.create(name="test_vm", token=uuid.uuid4(), cluster=which_cluster(),
                                      service=service, network_configuration=NetworkConfig.get_free_host_config())
        return site

    def test_no_permission_views_tests(self):
        cluster = Cluster.objects.create(name="mws-test-1")
        Host.objects.create(hostname="mws-test-1.dev.mws3.cam.ac.uk", cluster=cluster)
        site = Site.objects.create(name="testSite", start_date=datetime.today(), type=ServerType.objects.get(id=1))
        service = Service.objects.create(site=site, type='production', status="ready",
                                         network_configuration=NetworkConfig.get_free_prod_service_config())
        vm = VirtualMachine.objects.create(name="test_vm", token=uuid.uuid4(), cluster=which_cluster(),
                                           service=service, network_configuration=NetworkConfig.get_free_host_config())
        vhost = Vhost.objects.create(name="default", service=service)
        dn = DomainName.objects.create(name="testtestest.mws3test.csx.cam.ac.uk", status="accepted", vhost=vhost)
        unix_group = UnixGroup.objects.create(name="testUnixGroup", service=service)

        # TODO test index empty
        self.assertEqual(self.client.get(site.get_absolute_url()).status_code, 403)
        self.assertEqual(self.client.get(reverse('editsite', kwargs={'site_id': site.id})).status_code, 403)
        self.assertEqual(self.client.get(reverse(views.service_settings,
                                                 kwargs={'service_id': service.id})).status_code, 403)
        self.assertEqual(self.client.get(reverse('billing_management',
                                                 kwargs={'site_id': site.id})).status_code, 403)
        self.assertEqual(self.client.get(reverse('deletesite', kwargs={'site_id': site.id})).status_code, 403)
        self.assertEqual(self.client.get(reverse('disablesite', kwargs={'site_id': site.id})).status_code, 403)
        self.assertEqual(self.client.get(reverse('enablesite', kwargs={'site_id': site.id})).status_code, 403)
        self.assertEqual(self.client.get(reverse('listvhost',
                                                 kwargs={'service_id': service.id})).status_code, 403)
        self.assertEqual(self.client.get(reverse('createvhost', kwargs={'service_id': service.id})).status_code, 403)
        self.assertEqual(self.client.get(reverse('sitesmanagement.views.clone_vm_view', kwargs={'site_id': site.id})).status_code, 403)
        self.assertEqual(self.client.get(reverse('mwsauth.views.auth_change',
                                                 kwargs={'site_id': site.id})).status_code, 403)
        self.assertEqual(self.client.get(reverse(views.delete_vm, kwargs={'service_id': service.id})).status_code, 403)
        self.assertEqual(self.client.get(reverse(views.power_vm, kwargs={'service_id': service.id})).status_code, 403)
        self.assertEqual(self.client.get(reverse(views.reset_vm, kwargs={'service_id': service.id})).status_code, 403)
        self.assertEqual(self.client.get(reverse('listunixgroups',
                                                 kwargs={'service_id': service.id})).status_code, 403)
        self.assertEqual(self.client.get(reverse('listunixgroups',
                                                 kwargs={'service_id': service.id})).status_code, 403)
        self.assertEqual(self.client.get(reverse('createunixgroup',
                                                 kwargs={'service_id': service.id})).status_code, 403)
        self.assertEqual(self.client.get(reverse('listvhost', kwargs={'service_id': service.id})).status_code, 403)
        self.assertEqual(self.client.get(reverse('listdomains',
                                                 kwargs={'vhost_id': vhost.id})).status_code, 403)
        self.assertEqual(self.client.get(reverse('deletevhost', kwargs={'vhost_id': vhost.id})).status_code, 403)
        self.assertEqual(self.client.get(reverse(views.certificates, kwargs={'vhost_id': vhost.id})).status_code, 403)
        self.assertEqual(self.client.get(reverse(views.add_domain, kwargs={'vhost_id': vhost.id})).status_code, 403)
        self.assertEqual(self.client.get(reverse('deletedomain', kwargs={'domain_id': dn.id})).status_code, 403)
        self.assertEqual(self.client.get(reverse(views.set_dn_as_main, kwargs={'domain_id': dn.id})).status_code, 403)
        self.assertEqual(self.client.get(reverse('updateunixgroup', kwargs={'ug_id': unix_group.id})).status_code, 403)
        self.assertEqual(self.client.get(reverse('deleteunixgroup',
                                                 kwargs={'ug_id': unix_group.id})).status_code, 403)

    def test_vm_is_busy(self):
        site = self.create_site()
        service = site.production_service
        service.status = "requested"
        service.save()
        service2 = Service.objects.create(site=site, type='test', status="requested",
                                          network_configuration=NetworkConfig.get_free_prod_service_config())
        VirtualMachine.objects.create(name="test_vm2", token=uuid.uuid4(), service=service2, cluster=which_cluster(),
                                      network_configuration=NetworkConfig.get_free_host_config())
        vhost = Vhost.objects.create(name="default", service=service)
        dn = DomainName.objects.create(name="testtestest.mws3test.csx.cam.ac.uk", status="accepted", vhost=vhost)
        unix_group = UnixGroup.objects.create(name="testUnixGroup", service=service)

        # TODO test index not empty
        self.assertRedirects(self.client.get(reverse('editsite', kwargs={'site_id': site.id})),
                             expected_url=site.get_absolute_url())
        self.assertRedirects(self.client.get(reverse(views.service_settings, kwargs={'service_id': service.id})),
                             expected_url=site.get_absolute_url())
        self.assertEqual(self.client.get(reverse('billing_management', kwargs={'site_id': site.id})).status_code, 200)
        # self.assertRedirects(self.client.get(reverse('deletesite', kwargs={'site_id': site.id})),
        #                      expected_url=site.get_absolute_url())
        # self.assertRedirects(self.client.get(reverse('disablesite', kwargs={'site_id': site.id})),
        #                      expected_url=site.get_absolute_url())
        self.assertRedirects(self.client.get(reverse('enablesite', kwargs={'site_id': site.id})),
                             expected_url=reverse('listsites'))
        self.assertRedirects(self.client.get(reverse('listvhost', kwargs={'service_id': service.id})),
                             expected_url=site.get_absolute_url())
        self.assertRedirects(self.client.get(reverse('createvhost', kwargs={'service_id': service.id})),
                             expected_url=site.get_absolute_url())
        self.assertRedirects(self.client.get(reverse('mwsauth.views.auth_change', kwargs={'site_id': site.id})),
                             expected_url=site.get_absolute_url())
        self.assertEqual(self.client.get(reverse(views.delete_vm, kwargs={'service_id': service.id})).status_code, 403)
        # Primary VM cannot be deleted
        self.assertRedirects(self.client.get(reverse(views.delete_vm, kwargs={'service_id': service2.id})),
                             expected_url=site.get_absolute_url())
        self.assertRedirects(self.client.get(reverse(views.power_vm, kwargs={'service_id': service.id})),
                             expected_url=site.get_absolute_url())
        self.assertRedirects(self.client.get(reverse(views.reset_vm, kwargs={'service_id': service.id})),
                             expected_url=site.get_absolute_url())
        self.assertRedirects(self.client.get(reverse('listunixgroups', kwargs={'service_id': service.id})),
                             expected_url=site.get_absolute_url())
        self.assertRedirects(self.client.get(reverse('createunixgroup', kwargs={'service_id': service.id})),
                             expected_url=site.get_absolute_url())
        self.assertRedirects(self.client.get(reverse('listvhost', kwargs={'service_id': service.id})),
                             expected_url=site.get_absolute_url())
        self.assertRedirects(self.client.get(reverse('listdomains', kwargs={'vhost_id': vhost.id})),
                             expected_url=site.get_absolute_url())
        self.assertRedirects(self.client.get(reverse('deletevhost', kwargs={'vhost_id': vhost.id})),
                             expected_url=site.get_absolute_url())
        self.assertRedirects(self.client.get(reverse(views.certificates, kwargs={'vhost_id': vhost.id})),
                             expected_url=site.get_absolute_url())
        self.assertRedirects(self.client.get(reverse(views.add_domain, kwargs={'vhost_id': vhost.id})),
                             expected_url=site.get_absolute_url())
        self.assertRedirects(self.client.get(reverse('deletedomain', kwargs={'domain_id': dn.id})),
                             expected_url=site.get_absolute_url())
        self.assertRedirects(self.client.get(reverse(views.set_dn_as_main, kwargs={'domain_id': dn.id})),
                             expected_url=site.get_absolute_url())
        self.assertRedirects(self.client.get(reverse('updateunixgroup', kwargs={'ug_id': unix_group.id})),
                             expected_url=site.get_absolute_url())
        self.assertRedirects(self.client.get(reverse('deleteunixgroup', kwargs={'ug_id': unix_group.id})),
                             expected_url=site.get_absolute_url())

    def test_unix_groups(self):
        site = self.create_site()
        site.users.add(User.objects.create(username='amc203'))
        site.users.add(User.objects.create(username='jw35'))
        with mock.patch("apimws.ansible.subprocess") as mock_subprocess:
            mock_subprocess.check_output.return_value.returncode = 0
            response = self.client.post(reverse('createunixgroup',
                                                kwargs={'service_id': site.production_service.id}),
                                        {'unix_users': 'amc203,jw35', 'name': 'TESTUNIXGROUP'})
            self.assertIn(response.status_code, [200, 302])
            mock_subprocess.check_output.assert_called_with([
                "userv", "mws-admin", "mws_ansible_host",
                site.production_service.virtual_machines.first().network_configuration.name
            ], stderr=mock_subprocess.STDOUT)
        response = self.client.get(response.url)
        self.assertInHTML('<td>TESTUNIXGROUP</td>', response.content)
        self.assertInHTML('<td>amc203, jw35</td>', response.content)
        unix_group = UnixGroup.objects.get(name='TESTUNIXGROUP')
        self.assertSequenceEqual([User.objects.get(username='amc203'), User.objects.get(username='jw35')],
                                 unix_group.users.all())

        response = self.client.get(reverse('updateunixgroup', kwargs={'ug_id': unix_group.id}))
        self.assertInHTML('<input required id="id_name" maxlength="16" name="name" type="text" value="TESTUNIXGROUP" />',
                          response.content)
        self.assertContains(response, 'crsid: "amc203"')
        self.assertContains(response, 'crsid: "jw35"')

        with mock.patch("apimws.ansible.subprocess") as mock_subprocess:
            mock_subprocess.check_output.return_value.returncode = 0
            response = self.client.post(reverse('updateunixgroup', kwargs={'ug_id': unix_group.id}),
                                        {'unix_users': 'jw35', 'name': 'NEWTEST'})
            mock_subprocess.check_output.assert_called_with([
                "userv", "mws-admin", "mws_ansible_host",
                site.production_service.virtual_machines.first().network_configuration.name
            ], stderr=mock_subprocess.STDOUT)
        response = self.client.get(response.url)
        self.assertInHTML('<td>NEWTEST</td>', response.content, count=1)
        self.assertInHTML('<td>TESTUNIXGROUP</td>', response.content, count=0)
        self.assertInHTML('<td>jw35</td>', response.content, count=1)
        self.assertInHTML('<td>amc203</td>', response.content, count=0)

        with mock.patch("apimws.ansible.subprocess") as mock_subprocess:
            mock_subprocess.check_output.return_value.returncode = 0
            response = self.client.delete(reverse('deleteunixgroup', kwargs={'ug_id': unix_group.id}))
            mock_subprocess.check_output.assert_called_with([
                "userv", "mws-admin", "mws_ansible_host",
                site.production_service.virtual_machines.first().network_configuration.name
            ], stderr=mock_subprocess.STDOUT)
        response = self.client.get(reverse('listunixgroups', kwargs={'service_id': site.production_service.id}))
        self.assertInHTML('<td>NEWTEST</td>', response.content, count=0)
        self.assertInHTML('<td>jw35</td>', response.content, count=0)

    def test_vhosts_list(self):
        site = self.create_site()
        with mock.patch("apimws.ansible.subprocess") as mock_subprocess:
            mock_subprocess.check_output.return_value.returncode = 0
            response = self.client.post(reverse('createvhost', kwargs={'service_id': site.production_service.id}),
                                        {'name': 'testVhost'})
            self.assertIn(response.status_code, [200, 302])
            mock_subprocess.check_output.assert_called_with([
                "userv", "mws-admin", "mws_ansible_host",
                site.production_service.virtual_machines.first().network_configuration.name
            ], stderr=mock_subprocess.STDOUT)
        self.assertRedirects(response,
                             expected_url=reverse('listvhost', kwargs={'service_id': site.production_service.id}))
        response = self.client.get(reverse('listvhost', kwargs={'service_id': site.production_service.id}))
        self.assertInHTML('<td>testVhost</td>', response.content)
        vhost = Vhost.objects.get(name='testVhost')
        self.assertSequenceEqual([vhost], site.production_service.vhosts.all())

        with mock.patch("apimws.ansible.subprocess") as mock_subprocess:
            mock_subprocess.check_output.return_value.returncode = 0
            response = self.client.delete(reverse('deletevhost', kwargs={'vhost_id': vhost.id}))
            mock_subprocess.check_output.assert_called_with([
                "userv", "mws-admin", "mws_ansible_host",
                site.production_service.virtual_machines.first().network_configuration.name
            ], stderr=mock_subprocess.STDOUT)
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('listvhost', kwargs={'service_id': site.production_service.id}))
        self.assertInHTML('<td>testVhost</td>', response.content, count=0)

    def test_domains_management(self):
        site = self.create_site()

        with mock.patch("apimws.ansible.subprocess") as mock_subprocess:
            mock_subprocess.check_output.return_value.returncode = 0
            self.client.post(reverse('createvhost', kwargs={'service_id': site.production_service.id}),
                             {'name': 'testVhost'})

            vhost = Vhost.objects.get(name='testVhost')

            self.client.get(reverse(views.add_domain, kwargs={'vhost_id': vhost.id}))  # TODO check it

            with mock.patch("apimws.ipreg.subprocess") as api_ipreg:
                api_ipreg.check_output.return_value.returncode = 0
                def fake_subprocess_output(*args, **kwargs):
                    return '{"hostname":"test.mws3test.csx.cam.ac.uk","exists":[],"emails":["mws-support@uis.cam.ac.uk"],'\
                           '"message":"","status":0,"mzone":"MWS3","crsids":["AMC203","JMW11","JW35","MCV21"],' \
                           '"delegated":"N","domain":"mws3.csx.cam.ac.uk"}'
                api_ipreg.check_output.side_effect = fake_subprocess_output
                response = self.client.post(reverse(views.add_domain, kwargs={'vhost_id': vhost.id}),
                                            {'name': 'test.mws3test.csx.cam.ac.uk'})
            self.assertIn(response.status_code, [200, 302])
            mock_subprocess.check_output.assert_called_with([
                "userv", "mws-admin", "mws_ansible_host",
                site.production_service.virtual_machines.first().network_configuration.name
            ], stderr=mock_subprocess.STDOUT)

        response = self.client.get(reverse('listdomains', kwargs={'vhost_id': vhost.id}))
        self.assertInHTML(
            '''<tbody>
                    <tr>
                        <td>
                            <p>test.mws3test.csx.cam.ac.uk</p>
                        </td>
                        <td>
                            <p>Requested</p>
                        </td>
                        <td>
                            <p>Managed hostname</p>
                        </td>
                        <td style="width: 155px; cursor: pointer">
                            <p>
                            <a onclick="javascript:ajax_call('/set_dn_as_main/1/', 'POST')">
                                Set as main hostname
                            </a>
                            <a class="delete_domain" data-href="javascript:ajax_call('/delete_domain/1/', 'DELETE')">
                                <i title="Delete" class="fa fa-trash-o fa-2x" data-toggle="tooltip"></i>
                            </a>
                            </p>
                        </td>
                    </tr>
                </tbody>''', response.content, count=1)
        self.client.get(reverse(views.set_dn_as_main, kwargs={'domain_id': 1}))
        self.assertInHTML(
            '''<tbody>
                    <tr>
                        <td>
                            <p>test.mws3test.csx.cam.ac.uk</p>
                        </td>
                        <td>
                            <p>Requested</p>
                        </td>
                        <td>
                            <p>Managed hostname</p>
                        </td>
                        <td style="width: 155px; cursor: pointer">
                            <p>
                            <a onclick="javascript:ajax_call('/set_dn_as_main/1/', 'POST')">
                                Set as main hostname
                            </a>
                            <a class="delete_domain" data-href="javascript:ajax_call('/delete_domain/1/', 'DELETE')">
                                <i title="Delete" class="fa fa-trash-o fa-2x" data-toggle="tooltip"></i>
                            </a>
                            </p>
                        </td>
                    </tr>
                </tbody>''', response.content, count=1)
        with mock.patch("apimws.ansible.subprocess") as mock_subprocess:
            mock_subprocess.check_output.return_value.returncode = 0
            response = self.client.post(reverse(views.set_dn_as_main, kwargs={'domain_id': 1}))
            mock_subprocess.check_output.assert_called_with([
                "userv", "mws-admin", "mws_ansible_host",
                site.production_service.virtual_machines.first().network_configuration.name
            ], stderr=mock_subprocess.STDOUT)
        response = self.client.get(reverse('listdomains', kwargs={'vhost_id': vhost.id}))
        self.assertInHTML(
            '''<tbody>
                    <tr>
                        <td>
                            <p>test.mws3test.csx.cam.ac.uk
                                <br/>This is the current main hostname
                            </p>
                        </td>
                        <td>
                            <p>Requested</p>
                        </td>
                        <td>
                            <p>Managed hostname</p>
                        </td>
                        <td style="width: 155px; cursor: pointer">
                            <p>
                            <a onclick="javascript:ajax_call('/set_dn_as_main/1/', 'POST')">
                                Set as main hostname
                            </a>
                            <a class="delete_domain" data-href="javascript:ajax_call('/delete_domain/1/', 'DELETE')">
                                <i title="Delete" class="fa fa-trash-o fa-2x" data-toggle="tooltip"></i>
                            </a>
                            </p>
                        </td>
                    </tr>
                </tbody>''', response.content, count=1)
        with mock.patch("apimws.ansible.subprocess") as mock_subprocess:
            mock_subprocess.check_output.return_value.returncode = 0
            response = self.client.delete(reverse('deletedomain', kwargs={'domain_id': 1}))
            mock_subprocess.check_output.assert_called_with([
                "userv", "mws-admin", "mws_ansible_host",
                site.production_service.virtual_machines.first().network_configuration.name
            ], stderr=mock_subprocess.STDOUT)
        response = self.client.get(reverse('listdomains', kwargs={'vhost_id': vhost.id}))
        self.assertInHTML('''test.mws3test.csx.cam.ac.uk''', response.content, count=0)
        with mock.patch("apimws.ansible.subprocess") as mock_subprocess:
            mock_subprocess.check_output.return_value.returncode = 0
            response = self.client.post(reverse(views.add_domain, kwargs={'vhost_id': vhost.id}),
                                        {'name': 'externaldomain.com'})
            mock_subprocess.check_output.assert_called_with([
                "userv", "mws-admin", "mws_ansible_host",
                site.production_service.virtual_machines.first().network_configuration.name
            ], stderr=mock_subprocess.STDOUT)
        response = self.client.get(response.url)
        self.assertInHTML(
            ''' <tbody>
                    <tr>
                        <td>
                            <p>externaldomain.com
                                <br/>This is the current main hostname
                            </p>
                        </td>
                        <td>
                            <p>External</p>
                        </td>
                        <td>
                            <p><a class="setup_instructions" style="cursor: pointer;">Set up instructions</a></p>
                        </td>
                        <td style="width: 155px; cursor: pointer">
                            <p>
                                <a onclick="javascript:ajax_call('/set_dn_as_main/2/', 'POST')">
                                    Set as main hostname
                                </a>
                                <a class="delete_domain" data-href="javascript:ajax_call('/delete_domain/2/', 'DELETE')">
                                    <i title="Delete" class="fa fa-trash-o fa-2x" data-toggle="tooltip"></i>
                                </a>
                            </p>
                        </td>
                    </tr>
                </tbody>''', response.content, count=1)

    def test_root_pwd_message(self):
        site = self.create_site()

        # Test Jessie response
        AnsibleConfiguration.objects.update_or_create(service=site.production_service, key='os',
                                                      defaults={'value': 'jessie'})
        response = self.client.get(reverse('sitesmanagement.views.service_settings',
                                           kwargs={'service_id': site.production_service.id}))
        self.assertContains(response=response, text="Change database root password")
        response = self.client.get(reverse('change_db_root_password',
                                           kwargs={'service_id': site.production_service.id}))
        self.assertEqual(response.status_code, 200)

        # Test Stretch response
        AnsibleConfiguration.objects.update_or_create(service=site.production_service, key='os',
                                                      defaults={'value': 'stretch'})
        response = self.client.get(reverse('sitesmanagement.views.service_settings',
                                           kwargs={'service_id': site.production_service.id}))
        self.assertContains(response=response, text="""Root database passwords no longer apply, check mws help page""")
        response = self.client.get(reverse('change_db_root_password',
                                           kwargs={'service_id': site.production_service.id}))
        self.assertRedirects(response=response, expected_url=reverse('showsite', args=[str(site.id)]))


    # def test_certificates(self):
    #     site = self.create_site()
    #
    #     with mock.patch("apimws.ansible.subprocess") as mock_subprocess:
    #         mock_subprocess.check_output.return_value.returncode = 0
    #         response = self.client.post(reverse('createvhost', kwargs={'service_id': site.production_service.id}),
    #                                     {'name': 'testVhost'})
    #         self.assertIn(response.status_code, [200, 302])
    #         mock_subprocess.check_output.assert_called_with(["userv", "mws-admin", "mws_ansible"])
    #
    #     vhost = Vhost.objects.get(name='testVhost')
    #     response = self.client.post(reverse(views.generate_csr, kwargs={'vhost_id': vhost.id}))
    #     self.assertContains(response, "A CSR couldn't be generated because you don't have a master domain "
    #                                   "assigned to this vhost.")
    #     self.assertIsNone(vhost.csr)
    #
    #     with mock.patch("apimws.ansible.subprocess") as mock_subprocess:
    #         mock_subprocess.check_output.return_value.returncode = 0
    #         self.client.post(reverse(views.add_domain, kwargs={'vhost_id': vhost.id}), {'name': 'randomdomain.co.uk'})
    #         self.assertEqual(response.status_code, 200)
    #         mock_subprocess.check_output.assert_called_with(["userv", "mws-admin", "mws_ansible"])
    #
    #     vhost = Vhost.objects.get(name='testVhost')
    #     self.assertIsNone(vhost.csr)
    #     self.assertIsNone(vhost.certificate)
    #     self.assertIsNotNone(vhost.main_domain)
    #     self.client.post(reverse(views.generate_csr, kwargs={'vhost_id': vhost.id}))
    #     vhost = Vhost.objects.get(name='testVhost')
    #     self.assertIsNotNone(vhost.csr)
    #
    #     privatekeyfile = tempfile.NamedTemporaryFile()
    #     csrfile = tempfile.NamedTemporaryFile()
    #     certificatefile = tempfile.NamedTemporaryFile()
    #     subprocess.check_output(["openssl", "req", "-new", "-newkey", "rsa:2048", "-nodes", "-keyout",
    #                              privatekeyfile.name, "-subj", "/C=GB/CN=%s" % vhost.main_domain.name,
    #                              "-out", csrfile.name])
    #     subprocess.check_output(["openssl", "x509", "-req", "-days", "365", "-in", csrfile.name, "-signkey",
    #                              privatekeyfile.name, "-out", certificatefile.name])
    #
    #     certificatefiledesc = open(certificatefile.name, 'r')
    #     privatekeyfiledesc = open(privatekeyfile.name, 'r')
    #     self.client.post(reverse(views.certificates, kwargs={'vhost_id': vhost.id}),
    #                      {'key': privatekeyfile, 'cert': certificatefile})
    #     certificatefiledesc.close()
    #     privatekeyfiledesc.close()
    #     vhost = Vhost.objects.get(name='testVhost')
    #     self.assertIsNotNone(vhost.certificate)
    #
    #     certificatefile.seek(0)
    #     self.assertEqual(vhost.certificate, certificatefile.read())
    #
    #     privatekeyfile.seek(0)
    #     response = self.client.post(reverse(views.certificates, kwargs={'vhost_id': vhost.id}),
    #                                 {'cert': privatekeyfile})
    #     self.assertContains(response, "The certificate file is invalid")
    #
    #     certificatefile.seek(0)
    #     response = self.client.post(reverse(views.certificates, kwargs={'vhost_id': vhost.id}),
    #                                 {'key': certificatefile})
    #     self.assertContains(response, "The key file is invalid")
    #
    #     privatekeyfile.close()
    #     privatekeyfile = tempfile.NamedTemporaryFile()
    #     subprocess.check_output(["openssl", "genrsa", "-out", privatekeyfile.name, "2048"])
    #
    #     certificatefile.seek(0)
    #     response = self.client.post(reverse(views.certificates, kwargs={'vhost_id': vhost.id}),
    #                                 {'key': privatekeyfile, 'cert': certificatefile})
    #     self.assertContains(response, "The key doesn&#39;t match the certificate")
    #
    #     privatekeyfile.close()
    #     csrfile.close()
    #     certificatefile.close()

    # def test_backups(self):
    #     site = self.create_site()
    #
    #     with mock.patch("apimws.ansible.subprocess") as mock_subprocess:
    #         mock_subprocess.check_output.return_value.returncode = 0
    #         response = self.client.post(reverse('createvhost', kwargs={'service_id': site.production_service.id}),
    #                                     {'name': 'testVhost'})
    #         self.assertIn(response.status_code, [200, 302])
    #         vhost = Vhost.objects.get(name='testVhost')
    #         response = self.client.post(reverse(views.add_domain, kwargs={'vhost_id': vhost.id}),
    #                                     {'name': 'testDomain.cam.ac.uk'})
    #         self.assertIn(response.status_code, [200, 302])
    #         mock_subprocess.check_output.assert_called_with(["userv", "mws-admin", "mws_ansible_host",
    #                                                          site.production_service.virtual_machines.first()
    #                                                              .network_configuration.name])
    #
    #     restore_date = datetime.now()
    #
    #     with reversion.create_revision():
    #         domain = DomainName.objects.get(name='testDomain.cam.ac.uk')
    #         domain.name = "error"
    #         domain.status = 'accepted'
    #         domain.save()
    #
    #     self.client.post(reverse(views.backups, kwargs={'service_id': vhost.service.id}), {'backupdate': restore_date})
    #     domain = DomainName.objects.get(name='testDomain.cam.ac.uk')
    #     self.assertEqual(domain.status, 'accepted')
    #     self.assertEqual(domain.name, 'testDomain.cam.ac.uk')
