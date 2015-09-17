from django import forms
from apimws.models import ApacheModules


class ApacheModulesForm(forms.Form):
    apache_modules = forms.MultipleChoiceField(
        choices=tuple(ApacheModules.objects.filter(available=True).values_list('name','description')),
        label='', widget=forms.CheckboxSelectMultiple(), required=False)
