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

                vhost.certificate = certificates_str
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
