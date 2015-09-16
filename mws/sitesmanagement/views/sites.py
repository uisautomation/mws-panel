"""Views(Controllers) for managing Sites"""

import datetime
import logging
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse, reverse_lazy
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect
from django.utils.html import format_html
from django.views.generic import FormView, ListView, UpdateView
from django.views.generic.detail import SingleObjectMixin, DetailView
from ucamlookup import get_group_ids_of_a_user_in_lookup, IbisException, user_in_groups
from apimws.vm import new_site_primary_vm
from apimws.utils import email_confirmation
from mwsauth.utils import get_or_create_group_by_groupid
from sitesmanagement.forms import SiteForm
from sitesmanagement.models import NetworkConfig, Service, EmailConfirmation, Site, DomainName, Billing
from django.conf import settings as django_settings
from sitesmanagement.utils import can_create_new_site


LOGGER = logging.getLogger('mws')


def warning_messages(site):
    production_service = site.production_service
    test_service = site.test_service
    warning_messages_list = []

    if test_service is not None and test_service.status == 'ansible':
        warning_messages_list.append("Your test server is being configured.")

    if production_service is not None:
        if production_service.status == 'ansible':
            warning_messages_list.append("Your server is being configured.")

        if production_service.status == 'installing':
            warning_messages_list.append("Your server is being installed.")

        if production_service.status == 'requested':
            warning_messages_list.append("Your request in the Managed Web Service is being processed")

        if production_service.due_update():
            warning_messages_list.append("Your server is due to an OS update. From %s %.2f to %s %.2f" %
                                         (production_service.os_type, production_service.os_version,
                                          production_service.os_type,
                                          django_settings.OS_VERSION[production_service.os_type]))
        for domain_name in DomainName.objects.filter(vhost__service=production_service, status='requested'):
            warning_messages_list.append("Your domain name %s has been requested and is under review." %
                                         domain_name.name)
    else:
        warning_messages_list.append("Your request in the Managed Web Service is being processed")

    if not Billing.objects.filter(site=site).exists():
        warning_messages_list.append(
            format_html('No billing details are available, please <a href="%s" style="text-decoration: underline;">add '
                        'them</a>.' % reverse('sitesmanagement.views.billing_management', kwargs={'site_id': site.id})))

    if site.email:
        if EmailConfirmation.objects.filter(email=site.email, site_id=site.id, status='pending').exists():
            from apimws.views import resend_email_confirmation_view
            warning_messages_list.append(
                format_html('Your email \'%s\' is still unconfirmed, please check your email inbox and click on '
                            'the link of the email we sent you. <a id="resend_email_link" data-href="%s" href="#" '
                            'style="text-decoration: underline;">Resend confirmation email</a>' %
                            (site.email, reverse(resend_email_confirmation_view, kwargs={'site_id': site.id}))))

    return warning_messages_list


class LoginRequiredMixin(object):
    @classmethod
    def as_view(cls, **initkwargs):
        return login_required(super(LoginRequiredMixin, cls).as_view(**initkwargs))


class SitePriviledgeCheck(LoginRequiredMixin, SingleObjectMixin):
    model = Site
    context_object_name = 'site'
    pk_url_kwarg = 'site_id'

    def dispatch(self, request, *args, **kwargs):
        site = self.get_object()

        # If the user is not in the user auth list of the site and neither belongs to a group in the group auth list or
        # the site is suspended or canceled return None
        try:
            if (site not in request.user.sites.all() and not user_in_groups(request.user, site.groups.all())) \
                    or site.is_admin_suspended() or site.is_canceled() or site.is_disabled():
                return HttpResponseForbidden()
            if site.production_service is None:
                return redirect(reverse('listsites'))
        except Exception:
            return HttpResponseForbidden()

        return super(SitePriviledgeCheck, self).dispatch(request, *args, **kwargs)


class SitePriviledgeAndBusyCheck(SitePriviledgeCheck):
    def dispatch(self, request, *args, **kwargs):
        site = self.get_object()

        if site.is_busy:
            return redirect(site)

        return super(SitePriviledgeAndBusyCheck, self).dispatch(request, *args, **kwargs)


class SiteList(LoginRequiredMixin, ListView):
    """View(Controller) of the index page that shows the list of sites where the user is authorised. These sites are
    separated in sites where the user is authorised as the admin and sites where the user is authorised as a simple
    user (only SSH access)"""
    template_name = 'index.html'

    def get_context_data(self, **kwargs):
        context = super(SiteList, self).get_context_data(**kwargs)
        context['sites_enabled'] = filter(lambda site: not site.is_canceled() and not site.is_disabled(),
                                          self.object_list)
        context['sites_disabled'] = filter(lambda site: not site.is_canceled() and site.is_disabled(),
                                           self.object_list)
        context['sites_authorised'] = filter(lambda site: not site.is_canceled() and not site.is_disabled(),
                                             self.request.user.sites_auth_as_user.all())
        context['deactivate_new'] = not can_create_new_site()
        return context

    def get_queryset(self):
        try:
            groups_id = get_group_ids_of_a_user_in_lookup(self.request.user)
        except IbisException:
            groups_id = []

        sites = []
        for group_id in groups_id:
            group = get_or_create_group_by_groupid(group_id)
            sites += group.sites.all()

        sites += self.request.user.sites.all()

        return sites


class SiteCreate(LoginRequiredMixin, FormView):
    """View(Controller) with a form to request a new MWS site. The controller checks that there are free network
    pre configurations in the database before creating the new site."""
    form_class = SiteForm
    template_name = 'mws/new.html'
    prefix = "siteform"
    success_url = reverse_lazy('listsites')

    def get_context_data(self, **kwargs):
        context = super(SiteCreate, self).get_context_data(**kwargs)
        context['breadcrumbs'] = {0: dict(name='New Manage Web Service site', url=reverse_lazy('newsite'))}
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
            email_confirmation(site)
        LOGGER.info(str(self.request.user.username) + " created a new site '" + str(site.name) + "'")
        super(SiteCreate, self).form_valid(form)
        return redirect(site)

    def dispatch(self, *args, **kwargs):
        if not can_create_new_site():  # TODO add prealocated HostNetworkConfigs
            return redirect(reverse_lazy('listsites'))
        return super(SiteCreate, self).dispatch(*args, **kwargs)


class SiteShow(SitePriviledgeCheck, DetailView):
    """View(Controller) to see the main menu of a Site with all its options. It also shows messages to the user."""
    template_name = 'mws/show.html'

    def get_context_data(self, **kwargs):
        context = super(SiteShow, self).get_context_data(**kwargs)
        context['breadcrumbs'] = {
            0: dict(name='Manage Web Service site: ' + str(self.object.name), url=self.object.get_absolute_url())
        }
        context['warning_messages'] = warning_messages(self.object)
        context['DEMO'] = getattr(django_settings, 'DEMO', False)
        context['stats_name'] = self.object.production_service.network_configuration.name.replace(".","_")
        return context


class SiteEdit(SitePriviledgeAndBusyCheck, UpdateView):
    """View(Controller) to edit the name, description of a site and access to delete and disable options"""
    template_name = 'mws/edit.html'
    form_class = SiteForm

    def get_context_data(self, **kwargs):
        context = super(SiteEdit, self).get_context_data(**kwargs)
        context['breadcrumbs'] = {
            0: dict(name='Manage Web Service site: ' + str(self.object.name), url=self.object.get_absolute_url()),
            1: dict(name='Manage Web Service account settings',
                    url=reverse('editsite', kwargs={'site_id': self.object.id}))
        }
        return context

    def form_valid(self, form):
        form.user = self.request.user
        return_value = super(SiteEdit, self).form_valid(form)
        if 'email' in form.changed_data:
            if self.object.email:
                email_confirmation(self.object)
                # TODO launch ansible to update webmaster email address in host?
        return return_value


class SiteDelete(SitePriviledgeAndBusyCheck, UpdateView):
    """View(Controller) to delete a site. The Site object is marked as cancelled but not deleted. The VMs associated
    to this Site are switched off but eventually they are deleted. We maintain the Site object to report and
    billing options."""
    template_name = 'mws/disable.html'

    def get_context_data(self, **kwargs):
        context = super(SiteDelete, self).get_context_data(**kwargs)
        context['breadcrumbs'] = {
            0: dict(name='Manage Web Service site: ' + str(self.object.name), url=self.object.get_absolute_url()),
            1: dict(name='Change information about your MWS',
                    url=reverse('editsite', kwargs={'site_id': self.object.id})),
            2: dict(name='Delete your MWS', url=reverse('deletesite', kwargs={'site_id': self.object.id}))
        }
        return context

    def post(self, request, *args, **kwargs):
        super(SiteDelete, self).post(request, *args, **kwargs)
        if request.POST.get('confirmation') == "yes":
            self.object.cancel()
            return redirect(reverse('listsites'))
        else:
            return redirect(self.object)


class SiteDisable(SitePriviledgeAndBusyCheck, UpdateView):
    """View(Controller) to disable a Site object. The VMs are switched off."""
    template_name = 'mws/disable.html'

    def get_context_data(self, **kwargs):
        context = super(SiteDisable, self).get_context_data(**kwargs)
        context['breadcrumbs'] = {
            0: dict(name='Manage Web Service site: ' + str(self.object.name), url=self.object.get_absolute_url()),
            1: dict(name='Change information about your MWS',
                    url=reverse('editsite', kwargs={'site_id': self.object.id})),
            2: dict(name='Disable your MWS site', url=reverse('disablesite',
                                                              kwargs={'site_id': self.object.id}))
        }
        return context

    def post(self, request, *args, **kwargs):
        super(SiteDisable, self).post(request, *args, **kwargs)
        self.object.disable()
        return redirect(reverse('listsites'))


@login_required
def site_enable(request, site_id):
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

    return redirect(reverse('listsites'))
