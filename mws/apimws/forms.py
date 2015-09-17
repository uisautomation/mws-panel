from django import forms
from apimws.models import ApacheModule, PHPLib


class ApacheModuleForm(forms.Form):
    apache_modules = forms.MultipleChoiceField(
        choices=tuple(ApacheModule.objects.filter(available=True).values_list('name','description')),
        label='', widget=forms.CheckboxSelectMultiple(), required=False)

class PHPLibForm(forms.Form):
    php_libs = forms.MultipleChoiceField(
        choices=tuple((phplib.name, phplib.name + " - " + phplib.description)
                      for phplib in PHPLib.objects.filter(available=True).order_by('name')),
        label='', widget=forms.CheckboxSelectMultiple(), required=False)
