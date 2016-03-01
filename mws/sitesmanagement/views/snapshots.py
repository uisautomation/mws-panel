"""Views(Controllers) for managing Snapshots"""
from django.core.urlresolvers import reverse
from django.db import IntegrityError
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import CreateView, DeleteView
from apimws.ansible import ansible_create_custom_snapshot, delete_snapshot
from sitesmanagement.forms import SnapshotForm
from sitesmanagement.models import Snapshot
from sitesmanagement.views.vhosts import ServicePriviledgeCheck


class SnapshotPriviledgeCheck(ServicePriviledgeCheck):
    def dispatch(self, request, *args, **kwargs):
        snapshot = get_object_or_404(Snapshot, pk=self.kwargs['snapshot_id'])
        self.snapshot = snapshot
        self.kwargs['service_id'] = snapshot.service.id
        return super(SnapshotPriviledgeCheck, self).dispatch(request, *args, **kwargs)


class SnapshotCreate(ServicePriviledgeCheck, CreateView):
    model = Snapshot
    form_class = SnapshotForm

    def get(self, request, *args, **kwargs):
        return redirect(reverse('sitesmanagement.views.backups', kwargs={'service_id': self.service.id}))

    def form_valid(self, form):
        if Snapshot.objects.filter(service=self.service).count() >= 2:
            form.add_error(None, "You can only create two snapshots")
            return self.form_invalid(form)
        self.object = form.save(commit=False)
        self.object.service = self.service
        try:
            self.object.save()
        except IntegrityError:
            form.add_error("name", "Name for that snapshot already exists")
            return self.form_invalid(form)
        ansible_create_custom_snapshot.delay(self.service, self.object)
        return redirect(reverse('sitesmanagement.views.backups', kwargs={'service_id': self.service.id}))

    def form_invalid(self, form):
        response = redirect('sitesmanagement.views.backups', service_id=self.service.id)
        key, value = form.errors.popitem()
        response['Location'] += '?error_message=%s' % value.data[0].messages[0]
        return response

    def get_success_url(self):
        return reverse('sitesmanagement.views.backups', kwargs={'service_id': self.service.id})


class SnapshotDelete(SnapshotPriviledgeCheck, DeleteView):
    model = Snapshot
    pk_url_kwarg = 'snapshot_id'

    def get(self, request, *args, **kwargs):
        return redirect(reverse('sitesmanagement.views.backups', kwargs={'service_id': self.service.id}))

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.pending_delete = True
        self.object.save()
        delete_snapshot.delay(self.object.service, self.object.id)
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse('sitesmanagement.views.backups', kwargs={'service_id': self.service.id})
