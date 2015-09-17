from django import forms
from apimws.models import ApacheModules, PHPLib


class ApacheModulesForm(forms.Form):
    apache_modules = forms.MultipleChoiceField(
        choices=tuple(ApacheModules.objects.filter(available=True).values_list('name','description')),
        label='', widget=forms.CheckboxSelectMultiple(), required=False)

class PHPLibForm(forms.Form):
    php_libs = forms.MultipleChoiceField(
        choices=tuple((phplib.name, phplib.name + " - " + phplib.description)
                      for phplib in PHPLib.objects.filter(available=True).order_by('name')),
        label='', widget=forms.CheckboxSelectMultiple(), required=False)
