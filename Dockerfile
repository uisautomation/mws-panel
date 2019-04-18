FROM debian:stretch

# Install additional Debian packages
RUN apt-get -y update && apt-get upgrade -y && apt-get install -y \
        vim python python-pip python-dev\
        openssl userv openssh-client \
        apache2 apache2-utils libapache2-mod-wsgi \
        libssl-dev libjpeg-dev netcat zlib1g-dev \
        libpq-dev build-essential git

# Update pip and install Python dependencies. Note that vmmanager is installed
# from a local copy of the source. We use pip install -e to install vmmanager so
# that, if a local developer mounts the vmmanager sources as a volume, changes
# in the sources are reflected within the container.
COPY mws/requirements.txt ./
COPY vmmanager /usr/src/vmmanager
RUN pip install /usr/src/vmmanager && \
        pip install --upgrade -r requirements.txt

# Provide wait-for-it within the container
COPY docker/wait-for-it.sh ./
RUN install wait-for-it.sh /usr/local/bin/wait-for-it

# Copy Apache config
COPY docker/apache.conf /etc/apache2/sites-available/000-default.conf

# Copy MWS webapp
COPY mws /usr/src/app

# Add volumes to allow overriding container contents with local directories for
# development.
VOLUME ["/usr/src/app"]
VOLUME ["/usr/src/vmmanager"]

# Environment variables to override Django settings module and default database
# configuration. Note: at least DJANGO_DB_PASSWORD should be set.
ENV DJANGO_SETTINGS_MODULE=mws.settings \
    DJANGO_DB_ENGINE=django.db.backends.postgresql_psycopg2 \
    DJANGO_DB_NAME=mws \
    DJANGO_DB_HOST=db \
    DJANGO_DB_PORT=5432 \
    DJANGO_DB_USER=panel

# Other variables:
#   DJANGO_DB_PASSWORD
#   DJANGO_EMAIL_HOST
#   DJANGO_EMAIL_PORT

WORKDIR /usr/src/app
EXPOSE 80
ENTRYPOINT ["apache2ctl", "-D", "FOREGROUND"]
