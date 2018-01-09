Setting up a development environment
====================================

This section outlines how you as a developer can set up a development
environment for the MWS panel.

You will need the following installed:

1. git
2. docker
3. docker-compose

Clone the main webapp repo and navigate to the ``mws`` directory:

.. code:: console

    git clone <url> mws-panel && cd mws-panel

Build the development container and launch the development server:

::

    sudo docker-compose up devel

At this point, the website will be live on http://localhost:8000 but
there is no data in the database. The ``initialise-developer-site.sh``
script performs an initial database migration and installs some test
data in the site. Two users are created, ``test0001`` and ``test0002``.
The ``test0001`` user is configured as a superuser. The script can be
run inside the webapp container:

::

    sudo docker-compose exec devel bash -xe ./docker/initialise-developer-site.sh

Now visit http://localhost:8000 and log in.

.. note::

    Should ``requirements.txt`` be changed, the container needs to be re-built
    via ``sudo docker-compose build``.

Manual migration
----------------

Database migrations may be run manually via the migrate command:

::

    sudo docker-compose exec devel ./manage.py migrate

Python and database shells
--------------------------

The ``shell`` subcommand to ``manage.py`` will launch a Python shell
initialised with the Django environment:

::

    sudo docker-compose exec devel pip install --upgrade ipython
    sudo docker-compose exec devel ./manage.py shell

The ``dbshell`` subcommand will launch a direct Postgres shell. You'll
need the Postgres password which can be read from the
``docker-compose.yml`` file.

::

    sudo docker-compose exec devel apt install postgresql-client
    sudo docker-compose exec devel ./manage.py dbshell

Apache deployment
-----------------

The container supports Apache 2 as a web server. Run via:

.. code::

    sudo docker-compose up devel-apache

.. note::

    The Apache service name is different so if you want to run programs inside
    the container, make sure to change ``devel`` to ``devel-apache`` as
    appropriate when issuing commands from this document.
