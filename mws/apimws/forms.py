from django import forms
from apimws.models import PHPLib


class PHPLibForm(forms.Form):

    def __init__(self, *args, **kwargs):
        service = kwargs.pop('service')
        super(PHPLibForm, self).__init__(*args, **kwargs)
        self.fields["php_libs"] = forms.MultipleChoiceField(
            choices=tuple((phplib.name, phplib.os_dep_name(service) + " - " + phplib.description)
                          for phplib in PHPLib.objects.filter(available=True).order_by('name')),
            label='', widget=forms.SelectMultiple(), required=False)
