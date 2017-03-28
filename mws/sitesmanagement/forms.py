from django import forms
from sitesmanagement.models import Site, Vhost, DomainName, Billing, UnixGroup, Snapshot, ServerType


class SiteForm(forms.ModelForm):
    description = forms.CharField(label='Description for the MWS server (e.g. Web server for St Botolph\'s '
                                        'College main website)',
                                  widget=forms.Textarea(attrs={'maxlength': 250}),
                                  max_length=250,
                                  required=False)
    type = forms.ModelChoiceField(queryset=ServerType.objects.all().order_by('order'), empty_label=None)

    class Meta:
        model = Site
        fields = ('name', 'description', 'email', 'type')
        labels = {
            'name': 'A short name for this Managed Web Service Server (e.g. St Botolph\'s server)',
            'email': 'The webmaster email (please use a role email when possible)'
        }


class SiteFormEdit(SiteForm):
    class Meta(SiteForm.Meta):
        fields = ('name', 'description', 'email')


class SiteEmailForm(forms.ModelForm):
    class Meta:
        model = Site
        fields = ('email', )
        labels = {
            'email': 'The webmaster email (please use a role email when possible)'
        }


class VhostForm(forms.ModelForm):
    class Meta:
        model = Vhost
        fields = ('name', )
        labels = {
            'name': 'Web site name',
            # 'webapp': 'Optional pre-installed web application',
        }


class DomainNameFormNew(forms.ModelForm):
    special_case = forms.BooleanField(label='Special domain name (The user will be in charge of making the'
                                            'arrangments for *.cam.ac.uk domain names)', required=False)
    class Meta:
        model = DomainName
        fields = ('name', 'special_case')
        labels = {
            'name': 'Domain Name',
        }


class BillingForm(forms.ModelForm):
    class Meta:
        model = Billing
        fields = ('purchase_order_number', 'group', 'purchase_order')
        labels = {
            'purchase_order_number': 'Purchase order number (PO)',
            'group': 'Name of the team/group/department that raised the purchase order',
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
