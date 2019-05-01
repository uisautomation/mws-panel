"""Views(Controllers) for managing Unix Groups"""

from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.views.generic import ListView, CreateView, DeleteView, UpdateView
from ucamlookup import validate_crsid_list

from apimws.ansible import launch_ansible
from sitesmanagement.forms import UnixGroupForm
from sitesmanagement.models import UnixGroup
from sitesmanagement.views.vhosts import ServicePriviledgeCheck


class UnixGroupPriviledgeCheck(ServicePriviledgeCheck):
    def dispatch(self, request, *args, **kwargs):
        unix_group = get_object_or_404(UnixGroup, pk=self.kwargs['ug_id'])
        if unix_group.to_be_deleted:
            return HttpResponseForbidden()
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
            0: dict(name='Managed Web Service server: ' + str(self.site.name), url=self.site.get_absolute_url()),
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
        return self.service.unix_groups.filter(to_be_deleted=False)

    def dispatch(self, request, *args, **kwargs):
        return super(UnixGroupListView, self).dispatch(request, *args, **kwargs)


class UnixGroupCreate(ServicePriviledgeCheck, CreateView):
    """View(Controller) to add a new Unix Group to the service. It shows a form with the UnixGroup required fields."""
    model = UnixGroup
    form_class = UnixGroupForm
    template_name = 'mws/add_unix_group.html'

    def get_context_data(self, **kwargs):
        context = super(UnixGroupCreate, self).get_context_data(**kwargs)
        breadcrumbs = {
            0: dict(name='Managed Web Service server: ' + str(self.site.name), url=self.site.get_absolute_url()),
            1: dict(name='Server settings' if self.service.primary else 'Test server settings',
                    url=reverse('sitesmanagement.views.service_settings', kwargs={'service_id': self.service.id})),
            2: dict(name='Manage Unix Groups', url=reverse('listunixgroups', kwargs={'service_id': self.service.id})),
            3: dict(name='Add a new Unix Group', url=reverse('createunixgroup', kwargs={'service_id': self.service.id}))
        }
        context.update({
            'breadcrumbs': breadcrumbs,
            'site': self.site,
            'service': self.service,
        })
        return context

    def form_valid(self, form):
        try:
            self.object = form.save(commit=False)
            self.object.service = self.service
            self.object.save()
        except Exception:
            form.add_error(None, "A Unix Group already exists with that name")
            return self.form_invalid(form)

        unix_users = list(set(validate_crsid_list(self.request.POST.getlist('unix_users'))))

        if not all(user in self.object.service.site.list_of_all_type_of_users() for user in unix_users):
            form.add_error(None, "You have added users to this group that are not in the authorisation user list.")
            return self.form_invalid(form)

        self.object.users.add(*unix_users)

        launch_ansible(self.service)  # to apply these changes to the vm
        return super(UnixGroupCreate, self).form_valid(form)

    def get_success_url(self):
        return reverse('listunixgroups', kwargs={'service_id': self.service.id})

    def dispatch(self, request, *args, **kwargs):
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
            0: dict(name='Managed Web Service server: ' + str(self.site.name), url=self.site.get_absolute_url()),
            1: dict(name='Server settings' if self.service.primary else 'Test server settings',
                    url=reverse('sitesmanagement.views.service_settings', kwargs={'service_id': self.service.id})),
            2: dict(name='Manage Unix Groups', url=reverse('listunixgroups', kwargs={'service_id': self.service.id})),
            3: dict(name='Edit Unix Group', url=reverse('updateunixgroup', kwargs={'ug_id': self.object.id}))
        }
        context.update({
            'breadcrumbs': breadcrumbs,
            'site': self.site,
            'service': self.service,
            'unix_users': self.object.users.all()
        })
        return context

    def form_valid(self, form):
        self.object = form.save()

        unix_users = list(set(validate_crsid_list(self.request.POST.getlist('unix_users'))))

        if not all(user in self.object.service.site.list_of_all_type_of_users() for user in unix_users):
            form.add_error(None, "You have added users to this group that are not in the authorisation user list.")
            return self.form_invalid(form)

        self.object.users.clear()
        self.object.users.add(*unix_users)

        launch_ansible(self.service)  # to apply these changes to the vm
        return super(UnixGroupUpdate, self).form_valid(form)

    def get_success_url(self):
        return reverse('listunixgroups', kwargs={'service_id': self.service.id})

    def dispatch(self, request, *args, **kwargs):
        return super(UnixGroupUpdate, self).dispatch(request, *args, **kwargs)


class UnixGroupDelete(UnixGroupPriviledgeCheck, DeleteView):
    """View to delete the unix group selected."""
    model = UnixGroup
    pk_url_kwarg = 'ug_id'

    def get(self, request, *args, **kwargs):
        return HttpResponseRedirect(reverse('listunixgroups', kwargs={'service_id': self.service.id}))

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.to_be_deleted = True
        self.object.save()
        launch_ansible(self.service)
        return HttpResponse()

    def get_success_url(self):
        return reverse('listunixgroups', kwargs={'service_id': self.service.id})
