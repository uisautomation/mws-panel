"""Views(Controllers) for managing Vhosts"""
from OpenSSL import crypto
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.db import IntegrityError
from django.http import HttpResponseForbidden, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render, redirect
from django.views.generic import ListView, DeleteView, CreateView, DetailView
from ucamlookup import user_in_groups
from apimws.ansible import launch_ansible, delete_vhost_ansible, vhost_enable_apache_owned
from mwsauth.utils import privileges_check
from sitesmanagement.forms import VhostForm
from sitesmanagement.models import Service, Vhost
from sitesmanagement.views.sites import LoginRequiredMixin, warning_messages


CERTIFICATE_CHAINS = {
        'QuoVadis Global SSL ICA G2': '''-----BEGIN CERTIFICATE-----
MIIFTDCCAzSgAwIBAgIUSJgt4qkssznhyPkzNYJ10+T4glUwDQYJKoZIhvcNAQEL
BQAwRTELMAkGA1UEBhMCQk0xGTAXBgNVBAoTEFF1b1ZhZGlzIExpbWl0ZWQxGzAZ
BgNVBAMTElF1b1ZhZGlzIFJvb3QgQ0EgMjAeFw0xMzA2MDExMzM1MDVaFw0yMzA2
MDExMzM1MDVaME0xCzAJBgNVBAYTAkJNMRkwFwYDVQQKExBRdW9WYWRpcyBMaW1p
dGVkMSMwIQYDVQQDExpRdW9WYWRpcyBHbG9iYWwgU1NMIElDQSBHMjCCASIwDQYJ
KoZIhvcNAQEBBQADggEPADCCAQoCggEBAOHhhWmUwI9X+jT+wbho5JmQqYh6zle3
0OS1VMIYfdDDGeipY4D3t9zSGaNasGDZdrQdMlY18WyjnEKhi4ojNZdBewVphCiO
zh5Ni2Ak8bSI/sBQ9sKPrpd0+UCqbvaGs6Tpx190ZRT0Pdy+TqOYZF/jBmzBj7Yf
XJmWxlfCy62UiQ6tvv+4C6W2OPu1R4HUD8oJ8Qo7Eg0cD+GFsBM2w8soffyl+Dc6
pKtARmOClUC7EqyWP0V9953lA34kuJZlYxxdgghBTn9rWoaQw/Lr5Fn0Xgd7fYS3
/zGhmXYvVsuAxIn8Gk+YaeoLZ8H9tUvnDD3lEHzvIsMPxqtd7IgcVaMCAwEAAaOC
ASowggEmMBIGA1UdEwEB/wQIMAYBAf8CAQAwEQYDVR0gBAowCDAGBgRVHSAAMHIG
CCsGAQUFBwEBBGYwZDAqBggrBgEFBQcwAYYeaHR0cDovL29jc3AucXVvdmFkaXNn
bG9iYWwuY29tMDYGCCsGAQUFBzAChipodHRwOi8vdHJ1c3QucXVvdmFkaXNnbG9i
YWwuY29tL3F2cmNhMi5jcnQwDgYDVR0PAQH/BAQDAgEGMB8GA1UdIwQYMBaAFBqE
YrxITDMlBNTu0PYDxBlG0ZRrMDkGA1UdHwQyMDAwLqAsoCqGKGh0dHA6Ly9jcmwu
cXVvdmFkaXNnbG9iYWwuY29tL3F2cmNhMi5jcmwwHQYDVR0OBBYEFJEZYq1bF6cw
+/DeOSWxvYy5uFEnMA0GCSqGSIb3DQEBCwUAA4ICAQB8CmCCAEG1Lcw55fTba84A
ipwMieZydFO5bcIh5UyXWgWZ6OP4jb/6LaifEMLjRCC0mU14G6PrPU+iZQiIae7X
5EavhmETEA8JbLICjiD4c9Y6+bgMt4szEPiZ2SALOQj10Br4HKQfy/OvbedRbLax
p9qlDG4qJgSt3uikDIJSarx6mpgEQXu00UZNkiEYUfeO8hXGXrZbtDnkuaiVDtM6
s9yYpcoyFxFOrORrEgViaI7P3EJaDYmI6IDUIPaSBM6GrVMiaINYEMBL1v2jZi8r
XDY0yVsZ/0DAIQiCBNNvT1NjQ5Sn1E+O+ZBiqDD+rBvBoPsI6ydfdKtJur5YL+Oo
kJK2eLrce8287awIcd8FMRDcZw/NX1bc8uKye5OCtwpQ0d4jL4emuXwFv8TqUbZh
2xJShyy57cqw3qWoBOs/WWza29/Hun8PXkQoZepwY/xc+9nI1NaKM8NqhSqJNTJl
vXj7zb3mdpbe3YR9BkSXProlN7l5KOx54gJ7kJ7r6qJYJux03HyPM11Kp4wfdn1R
sC2UQ5awC6fg/3XE2HZVkyqJjKwqh4nFaiK5EMV7DHQ4oJx9ckmDw6pBvDaoPokX
yzdfJ72n+1JfHGP+workciKNldgqYX6J4jPrCIEIBrtDta4QxP10Tyd9RFu13XmE
8SYi/VXvrf3nriQfAZ/nSA==
-----END CERTIFICATE-----''',
        'QuoVadis Global SSL ICA G3': '''-----BEGIN CERTIFICATE-----
MIIGFzCCA/+gAwIBAgIUftbnnMmtgcTIGT75XUQodw40ExcwDQYJKoZIhvcNAQEL
BQAwSDELMAkGA1UEBhMCQk0xGTAXBgNVBAoTEFF1b1ZhZGlzIExpbWl0ZWQxHjAc
BgNVBAMTFVF1b1ZhZGlzIFJvb3QgQ0EgMiBHMzAeFw0xMjExMDYxNDUwMThaFw0y
MjExMDYxNDUwMThaME0xCzAJBgNVBAYTAkJNMRkwFwYDVQQKExBRdW9WYWRpcyBM
aW1pdGVkMSMwIQYDVQQDExpRdW9WYWRpcyBHbG9iYWwgU1NMIElDQSBHMzCCAiIw
DQYJKoZIhvcNAQEBBQADggIPADCCAgoCggIBANf8Od17be6c6lTGJDhEXpmkTs4y
Q39Rr5VJyBeWCg06nSS71s6xF3sZvKcV0MbXlXCYM2ZX7cNTbJ81gs7uDsKFp+vK
EymiKyEiI2SImOtECNnSg+RVR4np/xz/UlC0yFUisH75cZsJ8T1pkGMfiEouR0EM
7O0uFgoboRfUP582TTWy0F7ynSA6YfGKnKj0OFwZJmGHVkLs1VevWjhj3R1fsPan
H05P5moePFnpQdj1FofoSxUHZ0c7VB+sUimboHm/uHNY1LOsk77qiSuVC5/yrdg3
2EEfP/mxJYT4r/5UiD7VahySzeZHzZ2OibQm2AfgfMN3l57lCM3/WPQBhMAPS1jz
kE+7MjajM2f0aZctimW4Hasrj8AQnfAdHqZehbhtXaAlffNEzCdpNK584oCTVR7N
UR9iZFx83ruTqpo+GcLP/iSYqhM4g7fy45sNhU+IS+ca03zbxTl3TTlkofXunI5B
xxE30eGSQpDZ5+iUJcEOAuVKrlYocFbB3KF45hwcbzPWQ1DcO2jFAapOtQzeS+MZ
yZzT2YseJ8hQHKu8YrXZWwKaNfyl8kFkHUBDICowNEoZvBwRCQp8sgqL6YRZy0uD
JGxmnC2e0BVKSjcIvmq/CRWH7yiTk9eWm73xrsg9iIyD/kwJEnLyIk8tR5V8p/hc
1H2AjDrZH12PsZ45AgMBAAGjgfMwgfAwEgYDVR0TAQH/BAgwBgEB/wIBATARBgNV
HSAECjAIMAYGBFUdIAAwOgYIKwYBBQUHAQEELjAsMCoGCCsGAQUFBzABhh5odHRw
Oi8vb2NzcC5xdW92YWRpc2dsb2JhbC5jb20wDgYDVR0PAQH/BAQDAgEGMB8GA1Ud
IwQYMBaAFO3nb3Zav2DsSVvGpXe7chZxm8Q9MDsGA1UdHwQ0MDIwMKAuoCyGKmh0
dHA6Ly9jcmwucXVvdmFkaXNnbG9iYWwuY29tL3F2cmNhMmczLmNybDAdBgNVHQ4E
FgQUsxKJtalLNbwVAPCA6dh4h/ETfHYwDQYJKoZIhvcNAQELBQADggIBAFGm1Fqp
RMiKr7a6h707M+km36PVXZnX1NZocCn36MrfRvphotbOCDm+GmRkar9ZMGhc8c/A
Vn7JSCjwF9jNOFIOUyNLq0w4luk+Pt2YFDbgF8IDdx53xIo8Gv05e9xpTvQYaIto
qeHbQjGXfSGc91olfX6JUwZlxxbhdJH+rxTFAg0jcbqToJoScWTfXSr1QRcNbSTs
Y4CPG6oULsnhVvrzgldGSK+DxFi2OKcDsOKkV7W4IGg8Do2L/M588AfBnV8ERzpl
qgMBBQxC2+0N6RdFHbmZt0HQE/NIg1s0xcjGx1XW3YTOfje31rmAXKHOehm4Bu48
gr8gePq5cdQ2W9tA0Dnytb9wzH2SyPPIXRI7yNxaX9H8wYeDeeiKSSmQtfh1v5cV
7RXvm8F6hLJkkco/HOW3dAUwZFcKsUH+1eUJKLN18eDGwB8yGawjHvOKqcfg5Lf/
TvC7hgcx7pDYaCCaqHaekgUwXbB2Enzqr1fdwoU1c01W5YuQAtAx5wk1bf34Yq/J
ph7wNXGvo88N0/EfP9AdVGmJzy7VuRXeVAOyjKAIeADMlwpjBRhcbs9m3dkqvoMb
SXKJxv/hFmNgEOvOlaFsXX1dbKg1v+C1AzKAFdiuAIa62JzASiEhigqNSdqdTsOh
8W8hdONuKKpe9zKedhBFAvuxhDgKmnySglYc
-----END CERTIFICATE-----'''}


class ServicePriviledgeCheck(LoginRequiredMixin):
    def get_context_data(self, **kwargs):
        context = super(ServicePriviledgeCheck, self).get_context_data(**kwargs)
        context['sidebar_messages'] = warning_messages(self.site)
        return context

    def dispatch(self, request, *args, **kwargs):
        service = get_object_or_404(Service, pk=self.kwargs['service_id'])
        site = service.site
        self.site = site
        self.service = service

        # If the user is not in the user auth list of the site and neither belongs to a group in the group auth list or
        # the site is disabled or canceled return None
        try:
            if not request.user.is_superuser and \
                (site not in request.user.sites.all() and not user_in_groups(request.user, site.groups.all())) or \
                (site.is_canceled() or site.is_disabled()):
                return HttpResponseForbidden()
        except Exception:
            return HttpResponseForbidden()
        if not service or not service.active or service.is_busy:
            return redirect(site)
        return super(ServicePriviledgeCheck, self).dispatch(request, *args, **kwargs)


class VhostPriviledgeCheck(ServicePriviledgeCheck):
    def dispatch(self, request, *args, **kwargs):
        vhost = get_object_or_404(Vhost, pk=self.kwargs['vhost_id'])
        self.vhost = vhost
        self.kwargs['service_id'] = vhost.service.id
        return super(VhostPriviledgeCheck, self).dispatch(request, *args, **kwargs)


class VhostListView(ServicePriviledgeCheck, ListView):
    """View that shows the list of vhost associated to a service with service id passed by url kwargs"""
    model = Vhost
    template_name = 'mws/vhosts.html'

    def get_context_data(self, **kwargs):
        context = super(VhostListView, self).get_context_data(**kwargs)
        breadcrumbs = {
            0: dict(name='Managed Web Service server: ' + str(self.site.name), url=self.site.get_absolute_url()),
            1: dict(name='Server settings' if self.service.primary else 'Test server settings',
                    url=reverse('sitesmanagement.views.service_settings', kwargs={'service_id': self.service.id})),
            2: dict(name='Web sites management', url=reverse('listvhost', kwargs={'service_id': self.service.id}))
        }
        context.update({
            'breadcrumbs': breadcrumbs,
            'service': self.service,
            'site': self.site,
            'vhost_form': VhostForm(),
        })
        return context

    def get_queryset(self):
        return self.service.vhosts


class VhostCreate(ServicePriviledgeCheck, CreateView):
    """View(Controller) to add a new vhost to the service. It shows a form with the Vhost required fields."""
    model = Vhost
    form_class = VhostForm

    def get(self, request, *args, **kwargs):
        return redirect(self.get_success_url())

    def form_valid(self, form):
        try:
            self.object = form.save(commit=False)
            self.object.service = self.service
            self.object.save()
            launch_ansible(self.service)  # to create a new vhost configuration file
            return HttpResponseRedirect(self.get_success_url())
        except IntegrityError:
            messages.error(self.request, 'This website name already exists')
            return redirect(self.get_success_url())

    def form_invalid(self, form):
        messages.error(self.request, 'There was an error with the form submitted. Please check that the name of your'
                                     'website name is of less than 100 characters only contains alphabetical characters, '
                                     'numbers, hyphens, or underscores. Spaces are not permitted.')
        return redirect(self.site)

    def get_success_url(self):
        return reverse('listvhost', kwargs={'service_id': self.service.id})


class VisitVhost(VhostPriviledgeCheck, DetailView):
    """View(Controller) to redirect the user to the URL of the vhost selected."""
    model = Vhost
    pk_url_kwarg = 'vhost_id'

    def get(self, request, *args, **kwargs):
        super(VisitVhost, self).get(request, *args, **kwargs)
        return redirect("http://"+str(self.object.main_domain.name))


class VhostDelete(VhostPriviledgeCheck, DeleteView):
    """View to delete the vhost selected."""
    model = Vhost
    pk_url_kwarg = 'vhost_id'

    def get(self, request, *args, **kwargs):
        return HttpResponseRedirect(reverse('listvhost', kwargs={'service_id': self.service.id}))

    def delete(self, request, *args, **kwargs):
        vhost_name = self.vhost.name
        webapp = self.vhost.webapp
        service = self.vhost.service
        if vhost_name != "default":
            delete_vhost_ansible.delay(service, vhost_name, webapp)
            super(VhostDelete, self).delete(request, *args, **kwargs)
            launch_ansible(service)
            return HttpResponse("The website/vhost '%s' has been deleted successfully" % vhost_name)
        else:
            return HttpResponseForbidden("The default website/vhost cannot be deleted")

    def get_success_url(self):
        return reverse('listvhost', kwargs={'service_id': self.service.id})


@login_required
def generate_csr(request, vhost_id):
    vhost = get_object_or_404(Vhost, pk=vhost_id)
    site = privileges_check(vhost.service.site.id, request.user)

    if request.method == 'POST' and vhost.tls_key_hash != 'requested' and vhost.tls_key_hash != 'renewal':
        if vhost.main_domain is None:
            breadcrumbs = {
                0: dict(name='Managed Web Service server: ' + str(site.name), url=site.get_absolute_url()),
                1: dict(name='Server settings' if vhost.service.primary else 'Test server settings',
                        url=reverse('sitesmanagement.views.service_settings', kwargs={'service_id': vhost.service.id})),
                2: dict(name='Vhosts Management: %s' % vhost.name,
                        url=reverse('listvhost', kwargs={'service_id': vhost.service.id})),
                3: dict(name='TLS/SSL Certificates', url=reverse(certificates, kwargs={'vhost_id': vhost.id})),
            }

            return render(request, 'mws/certificates.html', {
                'breadcrumbs': breadcrumbs,
                'vhost': vhost,
                'service': vhost.service,
                'site': site,
                'error_main_domain': True
            })

        if vhost.tls_enabled:
            vhost.tls_key_hash = 'renewal'
            vhost.csr = None
            vhost.save()
        else:
            vhost.tls_key_hash = 'requested'
            vhost.certificate = None
            vhost.csr = None
            vhost.tls_enabled = False
            vhost.save()

        launch_ansible(vhost.service)

    return redirect(reverse(certificates, kwargs={'vhost_id': vhost.id}))


def csr_match_crt(csr, crt):
    try:
        x509 = crypto.load_certificate(crypto.FILETYPE_ASN1, crt)
    except crypto.Error:
        x509 = crypto.load_certificate(crypto.FILETYPE_PEM, crt)
    x509req = crypto.load_certificate_request(crypto.FILETYPE_PEM, csr)
    return crypto.dump_privatekey(crypto.FILETYPE_PEM, x509.get_pubkey()) == \
           crypto.dump_privatekey(crypto.FILETYPE_PEM, x509req.get_pubkey())


@login_required
def certificates(request, vhost_id):
    vhost = get_object_or_404(Vhost, pk=vhost_id)
    site = privileges_check(vhost.service.site.id, request.user)
    service = vhost.service

    if site is None:
        return HttpResponseForbidden()

    if not service or not service.active or service.is_busy:
        return redirect(site)

    if not vhost.domain_names.all():
        return redirect(reverse('listvhost', kwargs={'service_id': vhost.service.id}))

    breadcrumbs = {
        0: dict(name='Managed Web Service server: ' + str(site.name), url=site.get_absolute_url()),
        1: dict(name='Server settings' if vhost.service.primary else 'Test server settings',
                url=reverse('sitesmanagement.views.service_settings', kwargs={'service_id': vhost.service.id})),
        2: dict(name='Web sites management: %s' % vhost.name,
                url=reverse('listvhost', kwargs={'service_id': vhost.service.id})),
        3: dict(name='TLS/SSL Certificate', url=reverse(certificates, kwargs={'vhost_id': vhost.id})),
    }

    error_message = None

    if request.method == 'POST':
        try:
            if 'cert' in request.FILES:
                try:
                    certificates_str = request.FILES['cert'].file.read()
                    cert = crypto.load_certificate(crypto.FILETYPE_PEM, certificates_str)
                except Exception as e:
                    raise ValidationError("The certificate file is invalid")

                if vhost.csr is None:
                    raise ValidationError("CSR does not exists")

                if not csr_match_crt(vhost.csr, certificates_str):
                    raise ValidationError("The certificate doesn't match the CSR")

                issuer = None
                for component in cert.get_issuer().get_components():
                    if component[0] == 'CN':
                        issuer = component[1]
                if not issuer:
                    raise ValidationError("The certificate doesn't have any issuer")
                if issuer not in CERTIFICATE_CHAINS:
                    raise ValidationError("Certificate issuer unknown by MWS")

                vhost.certificate = certificates_str
                vhost.certificate_chain = CERTIFICATE_CHAINS[issuer]
                vhost.tls_enabled = True
                if vhost.tls_key_hash == 'renewal_waiting_cert':
                    vhost.tls_key_hash = 'renewal_cert'
                vhost.save()
                launch_ansible(service)
            else:
                raise ValidationError("No Certificate uploaded")
        except ValidationError as e:
            error_message = e.message

    return render(request, 'mws/certificates.html', {
        'breadcrumbs': breadcrumbs,
        'vhost': vhost,
        'service': vhost.service,
        'site': site,
        'sidebar_messages': warning_messages(site),
        'error_message': error_message
    })


@login_required
def vhost_onwership(request, vhost_id):
    vhost = get_object_or_404(Vhost, pk=vhost_id)
    site = privileges_check(vhost.service.site.id, request.user)
    service = vhost.service

    if site is None or (not service or not service.active or service.is_busy):
        return HttpResponseForbidden()

    if request.method == 'POST' and not vhost.apache_owned:
        vhost_enable_apache_owned.delay(vhost_id)
        return HttpResponse("The ownership of the '%s' website docroot folder has been changed to www-data "
                            "successfully. This change will only remain for one hour." % vhost.name)

    return HttpResponseForbidden("An error happened while changing ownership of the docroot folder of the '%s' "
                                 "website" % vhost.name)
