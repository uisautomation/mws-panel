"""Views(Controllers) for managing Unix Groups"""
from django.conf import settings

from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.http import HttpResponseForbidden, HttpResponseRedirect, HttpResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.views.generic import ListView, CreateView, DeleteView, UpdateView
from ucamlookup import validate_crsids
from apimws.ansible import launch_ansible
from mwsauth.utils import privileges_check
from sitesmanagement.forms import UnixGroupForm
from sitesmanagement.models import UnixGroup
from sitesmanagement.views.vhosts import ServicePriviledgeCheck


class UnixGroupPriviledgeCheck(ServicePriviledgeCheck):
    def dispatch(self, request, *args, **kwargs):
        unix_group = get_object_or_404(UnixGroup, pk=self.kwargs['ug_id'])
        self.unix_group = unix_group
        self.kwargs['service_id'] = unix_group.service.id
        return super(UnixGroupPriviledgeCheck, self).dispatch(request, *args, **kwargs)


class UnixGroupListView(ServicePriviledgeCheck, ListView):
    """View that shows the list of unix groups associated to a service with service id passed by url kwargs"""
    model = UnixGroup
    template_name = 'mws/unix_groups.html'

    def get_context_data(self, **kwargs):
        context = super(UnixGroupListView, self).get_context_data(**kwargs)
        breadcrumbs = {
            0: dict(name='Manage Web Service server: ' + str(self.site.name), url=self.site.get_absolute_url()),
            1: dict(name='Server settings' if self.service.primary else 'Test server settings',
                    url=reverse('sitesmanagement.views.service_settings', kwargs={'service_id': self.service.id})),
            2: dict(name='Manage Unix Groups', url=reverse('listunixgroups', kwargs={'service_id': self.service.id}))
        }
        context.update({
            'breadcrumbs': breadcrumbs,
            'service': self.service,
            'site': self.site,
        })
        return context

    def get_queryset(self):
        return self.service.unix_groups

    def dispatch(self, request, *args, **kwargs):
        if getattr(settings, 'DEMO', False):
            return HttpResponseRedirect(reverse('listsites'))
        return super(UnixGroupListView, self).dispatch(request, *args, **kwargs)


class UnixGroupCreate(ServicePriviledgeCheck, CreateView):
    """View(Controller) to add a new Unix Group to the service. It shows a form with the UnixGroup required fields."""
    model = UnixGroup
    form_class = UnixGroupForm
    template_name = 'mws/add_unix_group.html'

    def get_context_data(self, **kwargs):
        context = super(UnixGroupCreate, self).get_context_data(**kwargs)
        breadcrumbs = {
            0: dict(name='Manage Web Service server: ' + str(self.site.name), url=self.site.get_absolute_url()),
            1: dict(name='Server settings' if self.service.primary else 'Test server settings',
                    url=reverse('sitesmanagement.views.service_settings', kwargs={'service_id': self.service.id})),
            2: dict(name='Manage Unix Groups', url=reverse('listunixgroups', kwargs={'service_id': self.service.id})),
            3: dict(name='Add a new Unix Group', url=reverse('createunixgroup', kwargs={'service_id': self.service.id}))
        }
        context.update({
            'breadcrumbs': breadcrumbs,
            'site': self.site,
            'service': self.service,
            'lookup_lists': {
                'unix_users': []
            },  # TODO to be removed once django-ucam-lookup is modified
        })
        return context

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.service = self.service
        self.object.save()

        unix_users = validate_crsids(self.request.POST.get('unix_users'))
        # TODO If there are no users in the list return an Exception?
        self.object.users.add(*unix_users)

        launch_ansible(self.service)  # to apply these changes to the vm
        return super(UnixGroupCreate, self).form_valid(form)

    def get_success_url(self):
        return reverse('listunixgroups', kwargs={'service_id': self.service.id})

    def dispatch(self, request, *args, **kwargs):
        if getattr(settings, 'DEMO', False):
            return HttpResponseRedirect(reverse('listsites'))
        return super(UnixGroupCreate, self).dispatch(request, *args, **kwargs)


class UnixGroupUpdate(UnixGroupPriviledgeCheck, UpdateView):
    """View and edit the unix group selected."""
    model = UnixGroup
    form_class = UnixGroupForm
    template_name = 'mws/unix_group.html'
    pk_url_kwarg = 'ug_id'

    def get_context_data(self, **kwargs):
        context = super(UnixGroupUpdate, self).get_context_data(**kwargs)
        breadcrumbs = {
            0: dict(name='Manage Web Service server: ' + str(self.site.name), url=self.site.get_absolute_url()),
            1: dict(name='Server settings' if self.service.primary else 'Test server settings',
                    url=reverse('sitesmanagement.views.service_settings', kwargs={'service_id': self.service.id})),
            2: dict(name='Manage Unix Groups', url=reverse('listunixgroups', kwargs={'service_id': self.service.id})),
            3: dict(name='Edit Unix Group', url=reverse('updateunixgroup', kwargs={'ug_id': self.object.id}))
        }
        context.update({
            'breadcrumbs': breadcrumbs,
            'site': self.site,
            'service': self.service,
            'lookup_lists': {
                'unix_users': self.object.users.all()
            },  # TODO to be removed once django-ucam-lookup is modified
        })
        return context

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.service = self.service
        self.object.save()

        unix_users = validate_crsids(self.request.POST.get('unix_users'))
        # TODO If there are no users in the list return an Exception?
        self.object.users.clear()
        self.object.users.add(*unix_users)

        launch_ansible(self.service)  # to apply these changes to the vm
        return super(UnixGroupUpdate, self).form_valid(form)

        # The service shoulnd't have to be update. Make sure the modelform does not include the service. Check how the parent do things to do it the same way

    def get_success_url(self):
        return reverse('listunixgroups', kwargs={'service_id': self.service.id})

    def dispatch(self, request, *args, **kwargs):
        if getattr(settings, 'DEMO', False):
            return HttpResponseRedirect(reverse('listsites'))
        return super(UnixGroupUpdate, self).dispatch(request, *args, **kwargs)


class UnixGroupDelete(UnixGroupPriviledgeCheck, DeleteView):
    """View to delete the unix group selected."""
    model = UnixGroup
    pk_url_kwarg = 'ug_id'

    def get(self, request, *args, **kwargs):
        return HttpResponseRedirect(reverse('listunixgroups', kwargs={'service_id': self.service.id}))

    def delete(self, request, *args, **kwargs):
        super(UnixGroupDelete, self).delete(request, *args, **kwargs)
        launch_ansible(self.service)
        return HttpResponse()

    def get_success_url(self):
        return reverse('listunixgroups', kwargs={'service_id': self.service.id})
