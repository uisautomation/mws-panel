"""Views(Controllers) for managing Sites"""

import datetime
import logging
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse, reverse_lazy
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.html import format_html
from django.views.generic import FormView, ListView, UpdateView
from django.views.generic.detail import SingleObjectMixin, DetailView
from ucamlookup import user_in_groups, get_user_lookupgroups
from apimws.ansible import launch_ansible_site
from apimws.models import AnsibleConfiguration
from apimws.utils import email_confirmation
from sitesmanagement.cronjobs import check_num_preallocated_sites
from sitesmanagement.forms import SiteForm, SiteEmailForm, SiteFormEdit
from sitesmanagement.models import Site, DomainName, Billing, Vhost, ServerType
from django.conf import settings as django_settings
from sitesmanagement.utils import can_create_new_site


LOGGER = logging.getLogger('mws')


def warning_messages(site):
    production_service = site.production_service
    warning_messages_list = []

    if production_service is not None:
        if production_service.due_update():
            warning_messages_list.append("Your server is due to an OS update.")
        for domain_name in DomainName.objects.filter(vhost__service=production_service, status='requested'):
            warning_messages_list.append("Your domain name %s has been requested and is under review." %
                                         domain_name.name)

    if not Billing.objects.filter(site=site).exists():
        warning_messages_list.append(
            format_html('No billing details are available, please <a href="%s" style="text-decoration: underline;">add '
                        'them</a>.' % reverse('billing_management', kwargs={'site_id': site.id})))

    for vhost in Vhost.objects.filter(service__site=site, apache_owned=True):
        warning_messages_list.append(
            format_html('Your website/vhost "%s" docroot folder is currently temporary writable by the apache user.' %
                        vhost.name))

    for pwd in AnsibleConfiguration.objects.filter(service__site=site, key="mysql_root_password"):
        warning_messages_list.append(
            format_html('You have a new MySQL root password. Please visit the following <a href="%s" '
                        'style="text-decoration: underline;">URL</a> and follow the instructions to change '
                        'your temporary MySQL root password and make this message disappear.' %
                        reverse('change_db_root_password', kwargs={'service_id': pwd.service.id})))

    return warning_messages_list


class LoginRequiredMixin(object):
    @classmethod
    def as_view(cls, **initkwargs):
        return login_required(super(LoginRequiredMixin, cls).as_view(**initkwargs))


class SitePriviledgeCheck(LoginRequiredMixin, SingleObjectMixin):
    model = Site
    context_object_name = 'site'
    pk_url_kwarg = 'site_id'

    def get_context_data(self, **kwargs):
        context = super(SitePriviledgeCheck, self).get_context_data(**kwargs)
        context['sidebar_messages'] = warning_messages(self.object)
        return context

    def dispatch(self, request, *args, **kwargs):
        site = self.get_object()

        # If the user is not in the user auth list of the site and neither belongs to a group in the group auth list or
        # the site is disabled or canceled return None
        try:
            if not request.user.is_superuser and \
                (site not in request.user.sites.all() and not user_in_groups(request.user, site.groups.all())) or \
                (site.is_canceled() or site.is_disabled() or site.production_service is None):
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


class SiteList(LoginRequiredMixin, ListView):
    """View(Controller) of the index page that shows the list of sites where the user is authorised. These sites are
    separated in sites where the user is authorised as the admin and sites where the user is authorised as a simple
    user (only SSH access)"""
    template_name = 'index.html'
    fields = '__all__'

    def get_context_data(self, **kwargs):
        context = super(SiteList, self).get_context_data(**kwargs)
        context['sites_enabled'] = filter(lambda site: not site.is_canceled() and not site.is_disabled(),
                                          self.object_list)
        context['sites_disabled'] = filter(lambda site: not site.is_canceled() and site.is_disabled(),
                                           self.object_list)

        ssh_sites =  list(set(reduce(lambda grouplist, group: grouplist+list(group.sites_auth_as_user.all()),
                                     get_user_lookupgroups(self.request.user),
                                     list(self.request.user.sites_auth_as_user.all()))))

        context['sites_authorised'] = filter(lambda site: not site.is_canceled() and not site.is_disabled(),
                                             ssh_sites)
        context['deactivate_new'] = not can_create_new_site()
        context['features'] = ServerType.objects.get(id=1)
        return context

    def get_queryset(self):
        return list(set(reduce(lambda grouplist, group: grouplist+list(group.sites.all()),
                               get_user_lookupgroups(self.request.user), list(self.request.user.sites.all()))))


class SiteCreate(LoginRequiredMixin, FormView):
    """View(Controller) with a form to request a new MWS server. The controller checks that there are free network
    pre configurations in the database before creating the new server."""
    form_class = SiteForm
    template_name = 'mws/new.html'
    prefix = "siteform"
    success_url = reverse_lazy('listsites')
    fields = '__all__'

    def get_context_data(self, **kwargs):
        context = super(SiteCreate, self).get_context_data(**kwargs)
        context['breadcrumbs'] = {0: dict(name='New Managed Web Service server', url=reverse_lazy('newsite'))}
        return context

    def form_valid(self, form):
        # This method is called when valid form data has been POSTed.
        # It should return an HttpResponse.
        siteform = form.save(commit=False)
        preallocated_site = Site.objects.filter(preallocated=True, disabled=True, type=siteform.type).first()
        if not preallocated_site:
            form.add_error("type", "No MWS Servers available at this moment with this configuration as they are "
                                   "currently being built, please try again later (they usually take 20 minutes to "
                                   "build) or email %s if you have any question."
                           % getattr(django_settings, 'EMAIL_MWS3_SUPPORT', 'mws-support@uis.cam.ac.uk'))
            return self.form_invalid(form)
        preallocated_site.start_date = datetime.date.today()
        preallocated_site.name = siteform.name
        preallocated_site.description = siteform.description
        preallocated_site.email = siteform.email
        preallocated_site.disabled = False
        preallocated_site.preallocated = False
        preallocated_site.full_clean()
        preallocated_site.save()
        # Save user that requested the site
        preallocated_site.users.add(self.request.user)
        if preallocated_site.email:
            email_confirmation(preallocated_site)
        LOGGER.info(str(self.request.user.username) + " requested a new server '" + str(preallocated_site.name) + "'")
        preallocated_site.production_service.power_on()
        check_num_preallocated_sites.delay()
        return redirect(preallocated_site)

    def dispatch(self, *args, **kwargs):
        if not can_create_new_site():  # TODO add prealocated HostNetworkConfigs
            return redirect(reverse_lazy('listsites'))
        return super(SiteCreate, self).dispatch(*args, **kwargs)


class SiteShow(SitePriviledgeCheck, DetailView):
    """View(Controller) to see the main menu of a Site with all its options. It also shows messages to the user."""
    template_name = 'mws/show.html'
    fields = '__all__'

    def get_context_data(self, **kwargs):
        context = super(SiteShow, self).get_context_data(**kwargs)
        context['breadcrumbs'] = {
            0: dict(name='Managed Web Service server: ' + str(self.object.name), url=self.object.get_absolute_url())
        }
        context['MAIN_DOMAIN'] = getattr(django_settings, 'MAIN_DOMAIN', False)
        context['stats_name'] = self.object.production_service.network_configuration.name.replace(".","_")
        try:
            context['main_website'] = Vhost.objects.get(name="default", service=self.object.production_service)
        except:
            pass
        return context


class SiteEdit(SitePriviledgeAndBusyCheck, UpdateView):
    """View(Controller) to edit the name, description of a site and access to delete and disable options"""
    template_name = 'mws/edit.html'
    form_class = SiteFormEdit

    def get_context_data(self, **kwargs):
        context = super(SiteEdit, self).get_context_data(**kwargs)
        context['breadcrumbs'] = {
            0: dict(name='Managed Web Service server: ' + str(self.object.name), url=self.object.get_absolute_url()),
            1: dict(name='Managed Web Service account settings',
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


class SiteEditEmail(SitePriviledgeCheck, UpdateView):
    """View(Controller) to edit the email associated to a site"""
    form_class = SiteEmailForm
    fields = '__all__'

    def render_to_response(self, context, **response_kwargs):
        return redirect(self.object)

    def get_success_url(self):
        return reverse('showsite', kwargs={'site_id':self.get_object().id})

    def form_valid(self, form):
        form.user = self.request.user
        super(SiteEditEmail, self).form_valid(form)
        if 'email' in form.changed_data and self.object.email:
            email_confirmation(self.object)
            launch_ansible_site(self.object)
        return redirect(self.object)

    def form_invalid(self, form):
        messages.error(self.request, 'The email format is incorrect')
        return self.render_to_response(self.get_context_data(form=form))


class SiteDelete(SitePriviledgeCheck, UpdateView):
    """View(Controller) to delete a site. The Site object is marked as cancelled but not deleted. The VMs associated
    to this Site are switched off but eventually they are deleted. We maintain the Site object to report and
    billing options."""
    template_name = 'mws/delete.html'
    fields = '__all__'

    def get_context_data(self, **kwargs):
        context = super(SiteDelete, self).get_context_data(**kwargs)
        context['breadcrumbs'] = {
            0: dict(name='Managed Web Service server: ' + str(self.object.name), url=self.object.get_absolute_url()),
            1: dict(name='Change information about your MWS',
                    url=reverse('editsite', kwargs={'site_id': self.object.id})),
            2: dict(name='Delete your MWS', url=reverse('deletesite', kwargs={'site_id': self.object.id}))
        }
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if request.POST.get('confirmation') == "yes":
            self.object.cancel()
            return redirect(reverse('listsites'))
        else:
            return redirect(self.object)


class SiteDisable(SitePriviledgeCheck, UpdateView):
    """View(Controller) to disable a Site object. The VMs are switched off."""
    template_name = 'mws/disable.html'
    fields = '__all__'

    def get_context_data(self, **kwargs):
        context = super(SiteDisable, self).get_context_data(**kwargs)
        context['breadcrumbs'] = {
            0: dict(name='Managed Web Service server: ' + str(self.object.name), url=self.object.get_absolute_url()),
            1: dict(name='Change information about your MWS',
                    url=reverse('editsite', kwargs={'site_id': self.object.id})),
            2: dict(name='Disable your MWS server', url=reverse('disablesite',
                                                                kwargs={'site_id': self.object.id}))
        }
        return context

    def post(self, request, *args, **kwargs):
        self.get_object().disable()
        return redirect(reverse('listsites'))


@login_required
def site_enable(request, site_id):
    """View(Controller) to reenable a Site object. The VMs are switched on."""
    site = get_object_or_404(Site, pk=site_id)

    try:
        if not request.user.is_superuser and \
            (site not in request.user.sites.all() and not user_in_groups(request.user, site.groups.all())) \
            or site.is_admin_suspended() or site.is_canceled():
            return HttpResponseForbidden()
    except Exception:
        return HttpResponseForbidden()

    if request.method == 'POST':
        if site.enable():
            if request.user.is_superuser:
                return render(request, 'mws/admin/search.html', {'results': [site]})
            else:
                return redirect(site)

    return redirect(reverse('listsites'))


@login_required
def site_unsuspend(request, site_id):
    """View(Controller) to unsuspend a Site object."""
    site = get_object_or_404(Site, pk=site_id)

    try:
        if not request.user.is_superuser:
            return HttpResponseForbidden()
    except Exception:
        return HttpResponseForbidden()

    if request.method == 'POST':
        if site.unsuspend():
            return render(request, 'mws/admin/search.html', {'results': [site]})

    return HttpResponseForbidden()


class SiteDoNotRenew(SitePriviledgeCheck, UpdateView):
    """Schedules cancellation of the site for the end of the current billing period"""
    template_name = 'mws/donotrenew.html'

    def get_context_data(self, **kwargs):
        context = super(SiteDoNotRenew, self).get_context_data(**kwargs)
        context['breadcrumbs'] = {
            0: dict(name='Managed Web Service server: ' + str(self.object.name), url=self.object.get_absolute_url()),
            1: dict(name='Change information about your MWS',
                    url=reverse('editsite', kwargs={'site_id': self.object.id})),
            2: dict(name='Cancel subscription', url=reverse('donotrenew', kwargs={'site_id': self.object.id}))
        }
        return context

    def post(self, request, *args, **kwargs):
        site = self.get_object()
        site.subscription = False
        site.save()
        return redirect(reverse('editsite', kwargs={'site_id': site.id}))
