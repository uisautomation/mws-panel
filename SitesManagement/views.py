import datetime
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render
from SitesManagement.models import SiteForm


@login_required
def index(request):
    return render(request, 'index.html', {})


@login_required
def new(request):
    breadcrumbs = {}
    breadcrumbs[0] = dict(name='New Manage Web Server', url=reverse(new))

    if request.method == 'POST':  # If the form has been submitted...
        site_form = SiteForm(request.POST, user=request.user) # A bound form
        if site_form.is_valid():

            site = site_form.save(commit=False)
            site.start_date = datetime.date.today()
            site.save()

            # Save user that requested the site
            site.users.add(request.user)

            return HttpResponseRedirect(reverse('SitesManagement.views.show'))  # Redirect after POST
    else:
        site_form = SiteForm(user=request.user)  # An unbound form

    return render(request, 'mws/new.html', {
        'site_form': site_form,
        'breadcrumbs': breadcrumbs
    })


@login_required
def show(request):
    return render(request, 'index.html', {})


def privacy(request):
    return render(request, 'index.html', {})