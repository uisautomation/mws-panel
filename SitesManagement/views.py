import datetime
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, HttpResponseForbidden
from django.shortcuts import render, get_object_or_404, redirect
from .models import SiteForm, DomainNameForm, Site, BillingForm, DomainName, platforms_api_request


@login_required
def index(request):
    all_sites = request.user.sites.all().order_by('name')
    return render(request, 'index.html', {
        'all_sites': all_sites,
    })


@login_required
def new(request):
    breadcrumbs = {}
    breadcrumbs[0] = dict(name='New Manage Web Server', url=reverse(new))

    # TODO: FIX: if SiteForm's name field is empty then DomainNameForm errors are also shown
    if request.method == 'POST':  # If the form has been submitted...
        site_form = SiteForm(request.POST, prefix="siteform", user=request.user) # A bound form
        domain_form = DomainNameForm(request.POST, prefix="domainform")
        if site_form.is_valid():

            site = site_form.save(commit=False)
            site.start_date = datetime.date.today()
            site.save()

            # Save user that requested the site
            site.users.add(request.user)

            platforms_api_request(site, primary=True)

            return HttpResponseRedirect(reverse('SitesManagement.views.show', kwargs={'site_id': site.id}))  # Redirect after POST
    else:
        site_form = SiteForm(prefix="siteform", user=request.user)  # An unbound form
        domain_form = DomainNameForm(prefix="domainform")

    return render(request, 'mws/new.html', {
        'site_form': site_form,
        'domain_form': domain_form,
        'breadcrumbs': breadcrumbs
    })


@login_required
def show(request, site_id):
    site = get_object_or_404(Site, pk=site_id)

    if not site in request.user.sites.all():
        return HttpResponseForbidden()

    if site.is_admin_suspended():
        return HttpResponseForbidden()

    breadcrumbs = {}
    breadcrumbs[0] = dict(name='Manage Web Server: '+str(site.name), url=reverse(show, kwargs={'site_id': site.id}))

    warning_messages = []

    if not hasattr(site, 'billing'):
        warning_messages.append("No Billing, please add one.")

    return render(request, 'mws/show.html', {
        'breadcrumbs': breadcrumbs,
        'warning_messages': warning_messages,
        'site': site
    })


@login_required
def billing(request, site_id):
    site = get_object_or_404(Site, pk=site_id)

    if not site in request.user.sites.all():
        return HttpResponseForbidden()

    if site.is_admin_suspended():
        return HttpResponseForbidden()

    breadcrumbs = {}
    breadcrumbs[0] = dict(name='Manage Web Server: '+str(site.name), url=reverse(show, kwargs={'site_id': site.id}))
    #TODO Change this
    breadcrumbs[1] = dict(name='Billing', url=reverse(show, kwargs={'site_id': site.id}))

    if request.method == 'POST':  # If the form has been submitted...
        if hasattr(site, 'billing'):
            billing_form = BillingForm(request.POST, request.FILES, instance=site.billing) # A bound form
            if billing_form.is_valid():
                billing_form.save()
                return HttpResponseRedirect(reverse('SitesManagement.views.show', kwargs={'site_id': site.id}))  # Redirect after POST
        else:
            billing_form = BillingForm(request.POST, request.FILES) # A bound form
            if billing_form.is_valid():
                billing = billing_form.save(commit=False)
                billing.site = site
                billing.save()
                return HttpResponseRedirect(reverse('SitesManagement.views.show', kwargs={'site_id': site.id}))  # Redirect after POST
    elif hasattr(site, 'billing'):
        billing_form = BillingForm(instance=site.billing)
    else:
        billing_form = BillingForm()  # An unbound form

    return render(request, 'mws/billing.html', {
        'breadcrumbs': breadcrumbs,
        'site': site,
        'billing_form': billing_form
    })


def privacy(request):
    return render(request, 'index.html', {})