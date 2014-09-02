import uuid
from django.db import models
from sitesmanagement.models import Site


class SiteRequestDemo(models.Model):
    site = models.OneToOneField(Site, related_name='site_request_demo')
    date_submitted = models.TimeField()

    def demo_time_passed(self):
        self.site.primary_vm.name = uuid.uuid4()
        self.site.primary_vm.status = 'ready'
        for dns in self.site.domain_names:
            if dns.status == 'requested':
                dns.status = 'accepted'