from django import forms
from SitesManagement.models import VirtualMachine


class VMForm(forms.ModelForm):
    class Meta:
        model = VirtualMachine
        fields = ('name',)
