Management of Sites and VMs
===========================

.. automodule:: sitesmanagement

Preallocation of Sites
----------------------

As discussed in :any:`vmlifecycle`, the pre-allocation of sites is performed
nightly via a celery task:

.. autofunction:: sitesmanagement.cronjobs.check_num_preallocated_sites

This task then calls :py:func:`~apimws.utils.preallocate_new_site` to actually
allocate the site.

.. autofunction:: apimws.utils.preallocate_new_site

Scheduled tasks ("cronjobs")
----------------------------

Scheduled tasks inherit from one of two base classes:

.. autoclass:: sitesmanagement.cronjobs.ScheduledTaskWithFailure

.. autoclass:: sitesmanagement.cronjobs.FinanceTaskWithFailure
