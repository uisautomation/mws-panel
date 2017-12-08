Control Panel API
=================

The control panel exposes a number of API endpoints which are used by other
components to feed information back.

VM installation feedback
------------------------

The :py:class:`~apimws.views.post_installation` view's endpoint is used to
notify the panel that a VM has finished provisioning.

.. automodule:: apimws.views
    :members: post_installation
