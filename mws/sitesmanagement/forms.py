from django import forms
from ucamlookup import get_institutions
from sitesmanagement.models import Site, Vhost, DomainName, Billing, UnixGroup, Snapshot


class SiteForm(forms.ModelForm):
    institution_id = forms.ChoiceField(label='The University institution responsible for this site')
    description = forms.CharField(label='Description for the MWS (e.g. Web server for St Botolph\'s '
                                        'College main website)',
                                  widget=forms.Textarea(attrs={'maxlength': 250}),
                                  max_length=250,
                                  required=False)

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(SiteForm, self).__init__(*args, **kwargs)
        self.fields['institution_id'].choices = get_institutions(user)

    class Meta:
        model = Site
        fields = ('name', 'description', 'institution_id', 'email')
        labels = {
            'name': 'A short name for this Managed Web Service account (e.g. St Botolph\'s main site)',
            'email': 'The webmaster email (please use a role email when possible)'
        }


class VhostForm(forms.ModelForm):
    class Meta:
        model = Vhost
        fields = ('name', )
        labels = {
            'name': 'Web site name',
        }


class DomainNameFormNew(forms.ModelForm):
    # name = forms.CharField(max_length=250, required=True, label="Domain name",
    #                        validators=[DomainName.full_domain_validator])

    class Meta:
        model = DomainName
        fields = ('name', )
        labels = {
            'name': 'Domain Name',
        }


class BillingForm(forms.ModelForm):
    class Meta:
        model = Billing
        fields = ('purchase_order_number', 'group', 'purchase_order')
        labels = {
            'purchase_order_number': 'Purchase order number (PO)',
            'group': 'Name or Reference of the group that raised the purchase order',
            'purchase_order': 'A PDF file with the purchase order'
        }


class UnixGroupForm(forms.ModelForm):
    class Meta:
        model = UnixGroup
        fields = ('name', )


class SnapshotForm(forms.ModelForm):
    class Meta:
        model = Snapshot
        fields = ('name', )
        labels = {
            'name': 'Snapshot name',
        }
