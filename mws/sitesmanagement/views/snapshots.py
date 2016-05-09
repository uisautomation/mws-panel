"""Views(Controllers) for managing Snapshots"""
import datetime
from django.core.urlresolvers import reverse
from django.db import IntegrityError
from django.shortcuts import get_object_or_404, redirect
from django.utils import dateparse
from django.views.generic import CreateView, DeleteView, ListView
from apimws.ansible import ansible_create_custom_snapshot, delete_snapshot, restore_snapshot
from apimws.models import AnsibleConfiguration
from sitesmanagement.forms import SnapshotForm
from sitesmanagement.models import Snapshot
from sitesmanagement.utils import get_object_or_None
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
        return redirect(reverse('backups', kwargs={'service_id': self.service.id}))

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
        return redirect(reverse('backups', kwargs={'service_id': self.service.id}))

    def form_invalid(self, form):
        response = redirect('backups', service_id=self.service.id)
        key, value = form.errors.popitem()
        response['Location'] += '?error_message=%s' % value.data[0].messages[0]
        return response

    def get_success_url(self):
        return reverse('backups', kwargs={'service_id': self.service.id})


class SnapshotDelete(SnapshotPriviledgeCheck, DeleteView):
    model = Snapshot
    pk_url_kwarg = 'snapshot_id'

    def get(self, request, *args, **kwargs):
        return redirect(reverse('backups', kwargs={'service_id': self.service.id}))

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.pending_delete = True
        self.object.save()
        delete_snapshot.delay(self.object.service, self.object.id)
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse('backups', kwargs={'service_id': self.service.id})


class SnapshotListView(ServicePriviledgeCheck, ListView):
    """View that shows the list of unix groups associated to a service with service id passed by url kwargs"""
    model = Snapshot
    template_name = 'mws/backups.html'

    def valid_fromdate(self):
        fromdate = get_object_or_None(AnsibleConfiguration, service=self.service, key="backup_first_date")
        if fromdate:
            fromdate = datetime.datetime.strptime(fromdate.value, '%Y-%m-%d').date()
        else:
            fromdate =  datetime.date.today()-datetime.timedelta(days=30)
        if fromdate < self.site.start_date+datetime.timedelta(days=1):
            if self.site.exmws2:
                fromdate = self.site.exmws2
            else:
                fromdate = self.site.start_date+datetime.timedelta(days=1)
        return fromdate

    def get_context_data(self, **kwargs):
        context = super(SnapshotListView, self).get_context_data(**kwargs)
        breadcrumbs = {
            0: dict(name='Managed Web Service server: ' + str(self.site.name), url=self.site.get_absolute_url()),
            1: dict(name='Server settings' if self.service.primary else 'Test server settings',
                    url=reverse('sitesmanagement.views.service_settings', kwargs={'service_id': self.service.id})),
            2: dict(name='Manage snapshots/backups', url=reverse('backups', kwargs={'service_id': self.service.id}))
        }
        context.update({
            'breadcrumbs': breadcrumbs,
            'service': self.service,
            'site': self.site,
            'fromdate': self.valid_fromdate(),
            'todate': datetime.date.today()-datetime.timedelta(days=1),
            'snapshot_form': SnapshotForm(),
            'error_message_snap': self.request.session['backup_form_message']
            if 'backup_form_message' in self.request.session else None,
            'limit_snaps': Snapshot.objects.filter(service=self.service).count() >= 2
        })
        self.request.session['backup_form_message'] = ""
        return context

    def get_queryset(self):
        return self.service.snapshots.all()

    def post(self, request, *args, **kwargs):
        try:
            if 'snapshot_id' in request.POST:
                snapshot = Snapshot.objects.get(id=request.POST['snapshot_id'], service=self.service)
                restore_snapshot.delay(self.service, snapshot.name)
                request.session['backup_form_message'] = "Your snapshot is being restored"
            else:
                backup_date = dateparse.parse_date(request.POST['backupdate'])
                if backup_date is None or backup_date > datetime.date.today() or backup_date < self.valid_fromdate():
                    raise ValueError
                restore_snapshot.delay(self.service, backup_date.strftime("%Y-%m-%d"))
                request.session['backup_form_message'] = "Your backup is being restored"
        except ValueError:
            request.session['backup_form_message'] = "Incorrect date"
        except Exception as e:
            request.session['backup_form_message'] = str(e)
        return redirect(reverse('backups', kwargs={'service_id': self.service.id}))

    def dispatch(self, request, *args, **kwargs):
        return super(SnapshotListView, self).dispatch(request, *args, **kwargs)
