Management of Sites and VMs
===========================

.. automodule:: sitesmanagement

.. _data-model:

Site, Services and Virtual Machines, oh my!
-------------------------------------------

The MWS data model and terminology can be a little confusing. The core of the
data model revolves around the :py:class:`~sitesmanagement.models.Site`, the
:py:class:`~sitesmanagement.models.Service` and the
:py:class:`~sitesmanagement.models.VirtualMachine`.

The :py:class:`~.Site` represents what a user actually purchases: it
is the primary object which a user interacts with. An individual Site may have
multiple :py:class:`~.Service` instances associated with it. Usually there will
be two: "production" and "test". The Service represents an individual virtual
web server. The "production" service is where all web-traffic is sent for a
service and the "test" service provides a parallel version of the "production"
service which users may make use of to try upgrades, etc. to their website. A
service will have a domain name, IPv4 address and IPv6 address associated with
it by means of a :py:class:`~.NetworkConfig`.

A :py:class:`~.VirtualMachine` represents the actual virtual machine running the
Apache web server used to serve a particular Service.

.. automodule:: sitesmanagement.models
    :members: Site, Service, VirtualMachine

Preallocation of Sites
----------------------

As discussed in :any:`vmlifecycle`, the pre-allocation of sites is performed
nightly via a celery task:

.. autofunction:: sitesmanagement.cronjobs.check_num_preallocated_sites

This task then calls :py:func:`~apimws.utils.preallocate_new_site` to actually
allocate the site.

.. autofunction:: apimws.utils.preallocate_new_site

Once the site is configured, the Xen server will call the URL associated with
the :py:class:`apimws.views.post_installation` view.

Scheduled tasks ("cronjobs")
----------------------------

Scheduled tasks inherit from one of two base classes:

.. autoclass:: sitesmanagement.cronjobs.ScheduledTaskWithFailure

.. autoclass:: sitesmanagement.cronjobs.FinanceTaskWithFailure
