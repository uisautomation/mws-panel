# Setting up a development environment

This document outlines how you as a developer can set up a development
environment for the MWS panel.

You will need the following installed:

1. git
2. docker
3. docker-compose

Clone the panel webapp repo and navigate to the ``mws`` directory:

```console
git clone <...> webapp && cd webapp/mws
```

Build the development container and launch the development server:

```
sudo docker-compose up devel
```

At this point, the website will be live on http://localhost:8000 but there is no
data in the database. The ``initialise-developer-site.sh`` script performs an
initial database migration and installs some test data in the site. Two users
are created, ``test0001`` and ``test0002``. The ``test0001`` user is configured
as a superuser. A pre-allocated :py:mod:`~sitesmanagement.models.Site` and associated entities is also created. 
The script can be run inside the webapp container:

```
sudo docker-compose exec devel bash -xe ./scripts/initialise-developer-site.sh
```

There are several web endpoints now:

* http://localhost:8000/ - the login portal itself
* http://localhost:8025/ - "fake" mailbox showing mails sent by server

At this point all xen/ansible calls will fail. You can mock these calls by using the following django settings:

* VM_API = "apimws.xen_mock"
* ANSIBLE_IMPL = "apimws.ansible_mock"

Alternatively, if you wish to go straight to having a registered site, after running
`initialise-developer-site.sh`, run:

```
sudo docker-compose exec devel bash -xe ./scripts/enable-developer-site.sh
```

## Running tests

Test suites require some extra packages. Install them via:

```
sudo docker-compose exec devel pip install -r requirements_jenkins.txt
```

After that, the tests can be run via:

```
sudo docker-compose exec devel ./manage.py test --settings=mws.settings_jenkins
```

## Apache deployment

The container supports Apache 2 as a web server. Run via:

```
sudo docker-compose up devel-apache
```

**NOTE:** note that the Apache service name is different so if you want to run
programs inside the container, make sure to change ``devel`` to ``devel-apache``
as appropriate when issuing commands from this document.

## Manual migration

Database migrations may be run manually via the migrate command:

```
sudo docker-compose exec devel ./manage.py migrate
```

## Python and database shells

The ``shell`` subcommand to ``manage.py`` will launch a Python shell initialised
with the Django environment:

```
sudo docker-compose exec devel pip install --upgrade ipython
sudo docker-compose exec devel ./manage.py shell
```

The ``dbshell`` subcommand will launch a direct Postgres shell. You'll need the
Postgres password which can be read from the ``docker-compose.yml`` file.

```
sudo docker-compose exec devel apt install postgresql-client
sudo docker-compose exec devel ./manage.py dbshell
```

## vmmanager

The vmmanager utility is *copied* and installed into the container. However, the
``vmmanager`` directory in the root is mounted inside the container as
``/usr/src/vmmanager``. You can use ``pip install -e`` to use symlinks to allow
changes to ``vmmanager`` to be reflected in the container:

```
sudo docker-compose exec devel pip install -e /usr/src/vmmanager
```
