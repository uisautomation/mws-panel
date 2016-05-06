import calendar
import logging
import subprocess
from datetime import date, datetime, timedelta
from time import mktime
from celery import shared_task
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.mail import EmailMessage
from django.db.models import Q
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.views.decorators.csrf import csrf_exempt
from stronghold.decorators import public
from apimws.ansible import launch_ansible_async, AnsibleTaskWithFailure, ansible_change_mysql_root_pwd
from apimws.ipreg import get_nameinfo
from mwsauth.utils import get_or_create_group_by_groupid, privileges_check
from sitesmanagement.models import DomainName, EmailConfirmation, VirtualMachine, Billing, Site, Vhost
from ucamlookup import user_in_groups


logger = logging.getLogger('mws')


@login_required
def confirm_dns(request, dn_id, token=None):
    if token == None or token == "":
        return HttpResponseForbidden()
    dn = get_object_or_404(DomainName, pk=dn_id, token=token)
    nameinfo = get_nameinfo(dn.name)
    if nameinfo['exists'] and "C" not in nameinfo['exists']:
        changeable = False
    else:
        changeable = True
    if request.method == 'POST':
        dn.authorised_by = request.user
        if request.POST.get('accepted') == '1':
            if changeable is False:
                return render(request, 'api/confirm_dns.html', {'dn': dn, 'changeable': changeable,})
            dn.accept_it()
        else:
            dn.reject_it(request.POST.get('reason'))
    return render(request, 'api/confirm_dns.html', {'dn': dn, 'changeable': changeable,})


@login_required
def billing_total(request):
    # Check if the request.user is authorised to do so: member of the uis-finance or UIS Information Systems groups
    if not user_in_groups(request.user,
                          [get_or_create_group_by_groupid("101923"), get_or_create_group_by_groupid("101888")]):
        return HttpResponseForbidden()

    return render(request, 'api/finance_total.html', {
        'billings': Billing.objects.filter(site__deleted=False),
        'year_cost': settings.YEAR_COST,
    })


@login_required
def billing_month(request, year, month):
    # Check if the request.user is authorised to do so: member of the uis-finance or UIS Information Systems groups
    if not user_in_groups(request.user,
                          [get_or_create_group_by_groupid("101923"), get_or_create_group_by_groupid("101888")]):
        return HttpResponseForbidden()

    month = int(month)
    year = int(year)

    if not (1 <= month <= 12):
        return HttpResponseForbidden()

    if month == 1:
        inidate = date(year - 1, 12, 1)
    else:
        inidate = date(year, month - 1, 1)

    return render(request, 'api/finance_month.html', {
        'new_sites_billing': Billing.objects.filter(site__start_date__month=inidate.month,
                                                    site__start_date__year=inidate.year, site__deleted=False),
        'renewal_sites_billing': Billing.objects.filter(site__start_date__month=month,
                                                        site__start_date__lt=date(year, 1, 1), site__deleted=False),
        'year': year,
        'month': month,
        'year_cost': settings.YEAR_COST,
    })


@login_required
def confirm_email(request, ec_id, token):
    # TODO add a message to say that your email approval is pending
    # TODO add a message when doing the redirect to the site to inform the user that the email has been accepted
    email_confirmation = get_object_or_404(EmailConfirmation, pk=ec_id)

    # check that the token match

    if email_confirmation.token == token:
        email_confirmation.status = 'accepted'
        email_confirmation.save()
        logger.info(str(request.user.username) + " confirmed email '" + str(email_confirmation.email) + "'")
        # launch_ansible_site(email_confirmation.site)  # to update server email associated
        return redirect(email_confirmation.site)
    else:
        raise Exception  # TODO change this exception for an error message


@shared_task(base=AnsibleTaskWithFailure, default_retry_delay=120, max_retries=2)
def post_installOS(service):
    launch_ansible_async(service, ignore_host_key=True)
    if service.type == 'production':
        ansible_change_mysql_root_pwd(service)
    if service.type == 'test':
        subprocess.check_output(["userv", "mws-admin", "mws_clone",
                                 service.site.production_service.virtual_machines.first().name,
                                 service.virtual_machines.first().name])
    if service.site.preallocated:
        service.site.disable()


@public
@csrf_exempt
def post_installation(request):
    if request.method == 'POST':
        vm_id = request.POST['vm']
        token = request.POST['token']
        if not vm_id or not token:
            return HttpResponseForbidden()

        vm = VirtualMachine.objects.get(id=vm_id)

        if vm.token == token:
            service = vm.service
            if service.status != "installing":
                raise Exception("The service wasn't in the OS installation process")  # TODO raise custom exception
            service.status = 'postinstall'
            service.save()
            post_installOS.apply_async((service,), countdown=90)
            # Wait 90 seconds before launching ansible, this will allow the machine have time to complete the reboot
            return HttpResponse()

    return HttpResponseForbidden()


@public
@csrf_exempt
def post_recreate(request):
    if request.method == 'POST':
        vm_id = request.POST['vm']
        token = request.POST['token']
        if not vm_id or not token:
            return HttpResponseForbidden()

        vm = VirtualMachine.objects.get(id=vm_id)

        if vm.token == token:
            EmailMessage(
                subject="MWS3 VM Restore %s" % vm.network_configuration.name,
                body="VM finished restoring. Please restore the backup and execute ansible. "
                     "VM part of the MWS3 site id %s" % vm.service.site.id,
                from_email="Managed Web Service Support <%s>"
                           % getattr(settings, 'EMAIL_MWS3_SUPPORT', 'mws-support@uis.cam.ac.uk'),
                to=[getattr(settings, 'EMAIL_MWS3_SUPPORT', 'mws-support@uis.cam.ac.uk')],
                headers={'Return-Path': getattr(settings, 'EMAIL_MWS3_SUPPORT', 'mws-support@uis.cam.ac.uk')}
            ).send()

    return HttpResponseForbidden()


@login_required
def resend_email_confirmation_view(request, site_id):
    site = privileges_check(site_id, request.user)

    if site is None:
        return HttpResponseForbidden()

    if request.method == 'POST':
        from apimws.utils import send_email_confirmation
        send_email_confirmation.delay(site)
    else:
        return HttpResponseForbidden()

    return HttpResponse()


@public
def stats(request):
    return render(request, 'stats.html')


def add_months(sourcedate, months=1):
    month = sourcedate.month - 1 + months
    year = sourcedate.year + month / 12
    month = month % 12 + 1
    day = min(sourcedate.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


@public
def statsdatainuse(request):
    mws2sites = Site.objects.filter(exmws2=True).count()
    values = [[mktime(date(2016, 3, 1).timetuple())*1000, mws2sites], ]
    today = add_months(datetime.today().date())
    odate = date(2016, 5, 1) - timedelta(days=1)
    while odate < today:
        if odate > date(2016, 10, 1):
            mws2sites = 0
        values.append([
            mktime(odate.timetuple())*1000,
            Site.objects.filter(Q(start_date__lte=odate), Q(end_date__gt=odate) | Q(end_date__isnull=True),
                                Q(preallocated=False)).count() + mws2sites
        ])
        odate = add_months(odate)
    data = [{
      "key" : "MWS Servers",
      "values" : values
    }, ]
    return JsonResponse(data, safe=False)


@public
def statsdataactive(request):
    all = Site.objects.filter(Q(end_date__gt=datetime.today().date()) | Q(end_date__isnull=True), preallocated=False)
    external_domains = DomainName.objects.exclude(name__endswith="mws3.csx.cam.ac.uk")
    active = all.filter(services__vhosts__domain_names__in=external_domains).distinct().count()
    websites = Vhost.objects.filter(service__site__preallocated=False, service__site__end_date__isnull=True).count()
    live_websites = Vhost.objects.filter(service__site__preallocated=False, service__site__end_date__isnull=True)\
        .exclude(main_domain__name__endswith="mws3.csx.cam.ac.uk").count()
    values = [{'x': 'Total Websites', 'y': websites},
              {'x': 'Live Websites', 'y':live_websites},
              {'x': 'Test Websites', 'y': websites-live_websites},
              {'x': 'Total MWS Servers', 'y': all.count()},
              {'x': 'Live MWS Servers', 'y': active},
              {'x': 'Test MWS Servers', 'y': all.count()-active}]
    data = [{
      "key" : "MWS Servers",
      "values" : values
    }, ]
    return JsonResponse(data, safe=False)


@public
def statsdatarequests(request):
    values = [{
        'x': date(2016, 3, 1),
        'y': Site.objects.filter(exmws2=True).count()
    }, ]
    today = add_months(datetime.today().date())
    odate = date(2016, 5, 1) - timedelta(days=1)
    while odate < today:
        values.append({
            'x': mktime(odate.timetuple())*1000,
            'y': Site.objects.filter(start_date__month=odate.month, start_date__year=odate.year,
                                     preallocated=False).count(),
        })
        odate = add_months(odate)
    data = [{
      "key" : "MWS Servers",
      "values" : values
    }, ]
    return JsonResponse(data, safe=False)
