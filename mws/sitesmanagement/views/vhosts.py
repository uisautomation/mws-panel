"""Views(Controllers) for managing Vhosts"""
from Crypto.Util import asn1
import OpenSSL
from django import forms
from django.conf import settings as django_settings
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse, reverse_lazy
from django.db import IntegrityError
from django.http import HttpResponseForbidden, HttpResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.views.generic import ListView, DeleteView, CreateView, DetailView
from ucamlookup import user_in_groups
from apimws.ansible import launch_ansible
from mwsauth.utils import privileges_check
from sitesmanagement.forms import VhostForm
from sitesmanagement.models import Service, Vhost
from sitesmanagement.views.sites import LoginRequiredMixin


class ServicePriviledgeCheck(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        service = get_object_or_404(Service, pk=self.kwargs['service_id'])
        site = service.site
        self.site = site
        self.service = service

        # If the user is not in the user auth list of the site and neither belongs to a group in the group auth list or
        # the site is suspended or canceled return None
        try:
            if (site not in request.user.sites.all() and not user_in_groups(request.user, site.groups.all())) \
                    or site.is_admin_suspended() or site.is_canceled() or site.is_disabled():
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
    model = Vhost
    template_name = 'mws/vhosts.html'

    def get_context_data(self, **kwargs):
        context = super(VhostListView, self).get_context_data(**kwargs)
        breadcrumbs = {
            0: dict(name='Manage Web Service server: ' + str(self.site.name), url=self.site.get_absolute_url()),
            1: dict(name='Server settings' if self.service.primary else 'Test server settings',
                    url=reverse('sitesmanagement.views.service_settings', kwargs={'service_id': self.service.id})),
            2: dict(name='Web sites management', url=reverse('listvhost', kwargs={'service_id': self.service.id}))
        }
        context.update({
            'breadcrumbs': breadcrumbs,
            'service': self.service,
            'site': self.site,
            'vhost_form': VhostForm(),
            'DEMO': getattr(django_settings, 'DEMO', False)
        })
        return context

    def get_queryset(self):
        return self.service.vhosts


class VhostCreate(ServicePriviledgeCheck, CreateView):
    """View(Controller) to add a new vhost to the service. It shows a form with the Vhost required fields."""
    model = Vhost
    form_class = VhostForm

    def get(self, request, *args, **kwargs):
        return redirect(reverse('listvhost', kwargs={'service_id': self.service.id}))

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.service = self.service
        self.object.save()
        launch_ansible(self.service)  # to create a new vhost configuration file
        return super(VhostCreate, self).form_valid(form)

    def get_success_url(self):
        return reverse('listvhost', kwargs={'service_id': self.service.id})


class VisitVhost(VhostPriviledgeCheck, DetailView):
    """View(Controller) to redirect the user to the URL of the vhost selected."""
    model = Vhost
    pk_url_kwarg = 'vhost_id'

    def get(self, request, *args, **kwargs):
        return redirect("http://"+str(self.object.main_domain.name))


class VhostDelete(VhostPriviledgeCheck, DeleteView):
    """View to delete the vhost selected."""
    model = Vhost
    pk_url_kwarg = 'vhost_id'

    def delete(self, request, *args, **kwargs):
        super(VhostDelete, self).delete(request, *args, **kwargs)
        launch_ansible(self.service)
        return HttpResponse()

    def get_success_url(self):
        return self.site.get_absolute_url()


@login_required
def generate_csr(request, vhost_id):
    vhost = get_object_or_404(Vhost, pk=vhost_id)
    site = privileges_check(vhost.service.site.id, request.user)

    if request.method == 'POST' and vhost.tls_key_hash != 'requested':
        if vhost.main_domain is None:
            breadcrumbs = {
                0: dict(name='Manage Web Service server: ' + str(site.name), url=site.get_absolute_url()),
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

        vhost.tls_key_hash = 'requested'
        vhost.certificate = None
        vhost.csr = None
        vhost.tls_enabled = False
        vhost.save()
        launch_ansible(vhost.service)

    return redirect(reverse(certificates, kwargs={'vhost_id': vhost.id}))


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
        0: dict(name='Manage Web Service server: ' + str(site.name), url=site.get_absolute_url()),
        1: dict(name='Server settings' if vhost.service.primary else 'Test server settings',
                url=reverse('sitesmanagement.views.service_settings', kwargs={'service_id': vhost.service.id})),
        2: dict(name='Web sites management: %s' % vhost.name,
                url=reverse('listvhost', kwargs={'service_id': vhost.service.id})),
        3: dict(name='TLS/SSL Certificate', url=reverse(certificates, kwargs={'vhost_id': vhost.id})),
    }

    error_message = None

    if request.method == 'POST':
        c = OpenSSL.crypto

        if 'cert' in request.FILES:
            try:
                certificates_str = request.FILES['cert'].file.read()
                cert = c.load_certificate(c.FILETYPE_PEM, certificates_str)
            except Exception as e:
                error_message = "The certificate file is invalid"
                # raise ValidationError(e)

        if 'key' in request.FILES and error_message is None:
            try:
                key_str = request.FILES['key'].file.read()
                priv = c.load_privatekey(c.FILETYPE_PEM, key_str)
            except Exception as e:
                error_message = "The key file is invalid"
                # raise ValidationError(e)

        if 'cert' in request.FILES and 'key' in request.FILES and error_message is None:
            try:
                pub = cert.get_pubkey()

                pub_asn1 = c.dump_privatekey(c.FILETYPE_ASN1, pub)
                priv_asn1 = c.dump_privatekey(c.FILETYPE_ASN1, priv)

                pub_der = asn1.DerSequence()
                pub_der.decode(pub_asn1)
                priv_der = asn1.DerSequence()
                priv_der.decode(priv_asn1)

                pub_modulus = pub_der[1]
                priv_modulus = priv_der[1]

                if pub_modulus != priv_modulus:
                    error_message = "The key doesn't match the certificate"
                    # raise ValidationError(e)

            except Exception as e:
                error_message = "The key doesn't match the certificate"
                # raise ValidationError(e)

        if 'cert' in request.FILES and not error_message:
            vhost.certificate = certificates_str
            vhost.save()

    return render(request, 'mws/certificates.html', {
        'breadcrumbs': breadcrumbs,
        'vhost': vhost,
        'service': vhost.service,
        'site': site,
        'error_message': error_message
    })
