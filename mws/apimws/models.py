from django import forms
from django.db import models
from sitesmanagement.models import VirtualMachine, Site


class AnsibleConfiguration(models.Model):
    site = models.ForeignKey(Site)
    key = models.CharField(max_length=250, db_index=True)
    value = models.TextField()


class VMForm(forms.ModelForm):
    name = forms.CharField(max_length=250, required=True)

    def clean(self):
        super(VMForm, self).clean()
        cleaned_data = self.cleaned_data
        name = cleaned_data.get('name')

        if VirtualMachine.objects.filter(name=name).exists():
            self._errors['name'] = self.error_class(['This name already exists'])

        return cleaned_data

    class Meta:
        model = VirtualMachine
        fields = ('name', )