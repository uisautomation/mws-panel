"""Views(Controllers) for managing Sites"""

import datetime
import logging
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse, reverse_lazy
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render, redirect
from django.utils.html import format_html
from django.views.generic import FormView
from django.views.generic.detail import SingleObjectMixin, DetailView
from ucamlookup import get_group_ids_of_a_user_in_lookup, IbisException, user_in_groups
from apimws.platforms import new_site_primary_vm
from apimws.utils import email_confirmation
from mwsauth.utils import privileges_check, get_or_create_group_by_groupid
from sitesmanagement.forms import SiteForm
from sitesmanagement.models import NetworkConfig, Service, EmailConfirmation, Site
from django.conf import settings as django_settings
from sitesmanagement.utils import can_create_new_site


LOGGER = logging.getLogger('mws')


class LoginRequiredMixin(object):
    @classmethod
    def as_view(cls, **initkwargs):
        return login_required(super(LoginRequiredMixin, cls).as_view(**initkwargs))


class SitePriviledgeCheck(LoginRequiredMixin, SingleObjectMixin):
    model = Site
    def dispatch(self, request, *args, **kwargs):
        site = self.get_object()

        # If the user is not in the user auth list of the site and neither belongs to a group in the group auth list or
        # the site is suspended or canceled return None
        try:
            if (site not in request.user.sites.all() and not user_in_groups(request.user, site.groups.all())) \
                    or site.is_admin_suspended() or site.is_canceled() or site.is_disabled():
                return HttpResponseForbidden()
        except Exception:
            return HttpResponseForbidden()

        return super(SitePriviledgeCheck, self).dispatch(request, *args, **kwargs)


class SitePriviledgeAndBusyCheck(SitePriviledgeCheck):
    def dispatch(self, request, *args, **kwargs):
        site = self.get_object()

        if site.is_busy:
            return redirect(site)

        return super(SitePriviledgeAndBusyCheck, self).dispatch(request, *args, **kwargs)


@login_required
def index(request):
    """View(Controller) of the index page that shows the list of sites where the user is authorised. These sites are
    separated in sites where the user is authorised as the admin and sites where the user is authorised as a simple
    user (only SSH access)"""
    try:
        groups_id = get_group_ids_of_a_user_in_lookup(request.user)
    except IbisException:
        groups_id = []

    sites = []
    for group_id in groups_id:
        group = get_or_create_group_by_groupid(group_id)
        sites += group.sites.all()

    sites += request.user.sites.all()

    sites_enabled = filter(lambda site: not site.is_canceled() and not site.is_disabled(), sites)

    sites_disabled = filter(lambda site: not site.is_canceled() and site.is_disabled(), sites)

    sites_authorised = filter(lambda site: not site.is_canceled() and not site.is_disabled(),
                              request.user.sites_auth_as_user.all())

    return render(request, 'index.html', {
        'sites_enabled': sorted(set(sites_enabled)),
        'sites_disabled': sorted(set(sites_disabled)),
        'sites_authorised': sorted(set(sites_authorised)),
        'deactivate_new': not can_create_new_site()
    })


class SiteCreate(LoginRequiredMixin, FormView):
    """View(Controller) with a form to request a new MWS site. The controller checks that there are free network
    pre configurations in the database before creating the new site."""
    form_class = SiteForm
    template_name = 'mws/new.html'
    prefix = "siteform"

    def get_context_data(self, **kwargs):
        context = super(SiteCreate, self).get_context_data(**kwargs)
        context['breadcrumbs'] = {0: dict(name='New Manage Web Service server', url=reverse_lazy('newsite'))}
        return context

    def form_valid(self, form):
        # This method is called when valid form data has been POSTed.
        # It should return an HttpResponse.
        site = form.save(commit=False)
        site.start_date = datetime.date.today()
        prod_service_network_configuration = NetworkConfig.get_free_prod_service_config()
        test_service_network_configuration = NetworkConfig.get_free_test_service_config()
        host_network_configuration = NetworkConfig.get_free_host_config()
        if not prod_service_network_configuration or not test_service_network_configuration \
                or not host_network_configuration:
            raise ValidationError('A MWS site cannot be created at this moment')
        site.save()
        # Save user that requested the site
        site.users.add(self.request.user)
        prod_service = Service.objects.create(site=site, type='production',
                                              network_configuration=prod_service_network_configuration)
        test_service = Service.objects.create(site=site, type='test',
                                              network_configuration=test_service_network_configuration)
        new_site_primary_vm.delay(prod_service, host_network_configuration)
        if site.email:
            email_confirmation.delay(site)
        LOGGER.info(str(self.request.user.username) + " created a new site '" + str(site.name) + "'")
        return super(SiteCreate, self).form_valid(form)

    def dispatch(self, *args, **kwargs):
        if not can_create_new_site():  # TODO add prealocated HostNetworkConfigs
            return HttpResponseRedirect(reverse_lazy(index))
        return super(SiteCreate, self).dispatch(*args, **kwargs)


class SiteShow(SitePriviledgeCheck, DetailView):
    """View(Controller) to see the main menu of a Site with all its options. It also shows messages to the user."""
    template_name = 'mws/show.html'

    def get_context_data(self, **kwargs):
        context = super(SiteShow, self).get_context_data(**kwargs)
        context['breadcrumbs'] = {
            0: dict(name='Manage Web Service server: ' + str(self.object.name), url=self.object.get_absolute_url())
        }

        warning_messages = []
        production_service = self.object.production_service
        test_service = self.object.test_service

        if production_service is not None and production_service.status == 'ansible':
            warning_messages.append("Your server is being configured.")

        if production_service is not None \
                and (production_service.status == 'requested' or production_service.status == 'installing'):
            warning_messages.append("Your server is being installed.")

        if test_service is not None and test_service.status == 'ansible':
            warning_messages.append("Your test server is being configured.")

        if production_service is not None:
            if production_service.due_update():
                warning_messages.append("Your server is due to an OS update. From %s %.2f to %s %.2f" %
                                        (production_service.os_type, production_service.os_version,
                                         production_service.os_type,
                                         django_settings.OS_VERSION[production_service.os_type]))
            for vhost in production_service.vhosts.all():
                for domain_name in vhost.domain_names.all():
                    if domain_name.status == 'requested':
                        warning_messages.append("Your domain name %s has been requested and is under review." %
                                                domain_name.name)

        if not hasattr(self.object, 'billing'):
            warning_messages.append(format_html('No billing details are available, please <a href="%s" '
                                                'style="text-decoration: underline;">add them</a>.' %
                                                reverse('sitesmanagement.views.billing_management',
                                                        kwargs={'site_id': self.object.id})))

        if self.object.email:
            try:
                site_email = EmailConfirmation.objects.get(email=self.object.email, site_id=self.object.id)
                if site_email.status == 'pending':
                    from apimws.views import resend_email_confirmation_view
                    warning_messages.append(format_html('Your email \'%s\' is still unconfirmed, please check your email '
                                                        'inbox and click on the link of the email we sent you. <a '
                                                        'id="resend_email_link" data-href="%s" href="#" '
                                                        'style="text-decoration: underline;">Resend confirmation '
                                                        'email</a>' % (self.object.email,
                                                                       reverse(resend_email_confirmation_view,
                                                                               kwargs={'site_id': self.object.id}))))
            except EmailConfirmation.DoesNotExist:
                pass

        if production_service is None or production_service.status == 'requested':
            warning_messages.append("Your request in the Managed Web Service is being processed")

        context['warning_messages'] = warning_messages
        context['DEMO'] = getattr(django_settings, 'DEMO', False)
        return context


@login_required
def edit(request, site_id):
    """View(Controller) to edit the name, description of a site and access to delete and disable options"""
    site = privileges_check(site_id, request.user)

    if site is None:
        return HttpResponseForbidden()

    if site.is_busy:
        return redirect(site)

    breadcrumbs = {
        0: dict(name='Manage Web Service server: ' + str(site.name), url=site.get_absolute_url()),
        1: dict(name='Manage Web Service account settings',
                url=reverse('sitesmanagement.views.edit', kwargs={'site_id': site.id}))
    }

    if request.method == 'POST':
        site_form = SiteForm(request.POST, user=request.user, instance=site)
        if site_form.is_valid():
            site_form.save()
            if 'email' in site_form.changed_data:
                if site.email:
                    email_confirmation.delay(site)
                    # TODO launch ansible to update webmaster email address in host?
            return redirect(site)
    else:
        site_form = SiteForm(user=request.user, instance=site)

    return render(request, 'mws/edit.html', {
        'site_form': site_form,
        'site': site,
        'breadcrumbs': breadcrumbs
    })


@login_required
def delete(request, site_id):
    """View(Controller) to delete a site. The Site object is marked as cancelled but not deleted. The VMs associated
    to this Site are switched off but eventually they are deleted. We maintain the Site object to report and
    billing options."""
    site = privileges_check(site_id, request.user)

    if site is None:
        return HttpResponseForbidden()

    if site.is_busy:
        return redirect(site)

    breadcrumbs = {
        0: dict(name='Manage Web Service server: ' + str(site.name), url=site.get_absolute_url()),
        1: dict(name='Change information about your MWS',
                url=reverse('sitesmanagement.views.edit', kwargs={'site_id': site.id})),
        2: dict(name='Delete your MWS', url=reverse('sitesmanagement.views.delete', kwargs={'site_id': site.id}))
    }

    if request.method == 'POST':
        if request.POST.get('confirmation') == "yes":
            site.cancel()
            return redirect(index)
        else:
            return redirect(site)

    return render(request, 'mws/delete.html', {
        'site': site,
        'breadcrumbs': breadcrumbs
    })


@login_required
def disable(request, site_id):
    """View(Controller) to disable a Site object. The VMs are switched off."""
    site = privileges_check(site_id, request.user)

    if site is None:
        return HttpResponseForbidden()

    if site.is_busy:
        return redirect(site)

    breadcrumbs = {
        0: dict(name='Manage Web Service server: ' + str(site.name), url=site.get_absolute_url()),
        1: dict(name='Change information about your MWS',
                url=reverse('sitesmanagement.views.edit', kwargs={'site_id': site.id})),
        2: dict(name='Disable your MWS site', url=reverse('sitesmanagement.views.disable',
                                                          kwargs={'site_id': site.id}))
    }

    if request.method == 'POST':
        site.disable()
        return redirect(index)

    return render(request, 'mws/disable.html', {
        'breadcrumbs': breadcrumbs,
        'site': site,
    })


@login_required
def enable(request, site_id):
    """View(Controller) to reenable a Site object. The VMs are switched on."""
    site = get_object_or_404(Site, pk=site_id)

    try:
        if (site not in request.user.sites.all() and not user_in_groups(request.user, site.groups.all())) \
                or site.is_admin_suspended() or site.is_canceled():
            return HttpResponseForbidden()
    except Exception:
        return HttpResponseForbidden()

    if request.method == 'POST':
        if site.enable():
            return redirect(site)

    return redirect(index)
