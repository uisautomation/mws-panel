# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


php_lib_values = [
    ('libawl-php', 'Andrew''s Web Libraries - PHP Utility Libraries'),
    ('libarc-php', 'Flexible RDF system for semantic web and PHP practitioners'),
    ('libfpdf-tpl-php', 'PHP library to use PDF templates with FPDF'),
    ('libfpdi-php', 'PHP library for importing existing PDF documents into FPDF'),
    ('libgraphite-php', 'PHP Linked Data Library'),
    ('libgv-php5', 'PHP5 bindings for graphviz'),
    ('libkohana2-modules-php', 'lightweight PHP5 MVC framework (extension modules)'),
    ('libkohana2-php', 'lightweight PHP5 MVC framework'),
    ('libmarkdown-php', 'PHP library for rendering Markdown data'),
    ('libnusoap-php', 'SOAP toolkit for PHP'),
    ('liboauth-php', 'PHP library implementing the OAuth secure authentication protocol'),
    ('libow-php5', '"Dallas 1-wire support: PHP5 bindings"'),
    ('libownet-php', '"Dallas 1-wire support: PHP OWNet library"'),
    ('libpuzzle-php', 'quick similar image finder - PHP bindings'),
    ('libsparkline-php', 'sparkline graphing library for php'),
    ('php5-adodb', 'Extension optimising the ADOdb database abstraction library'),
    ('php5-apcu', 'APC User Cache for PHP 5'),
    ('php5-cgi', 'server-side, HTML-embedded scripting language (CGI binary)'),
    ('php5-dbg', 'Debug symbols for PHP5'),
    ('php5-dev', 'Files for PHP5 module development'),
    ('php5-enchant', 'Enchant module for php5'),
    ('php5-exactimage', 'fast image manipulation library (PHP bindings)'),
    ('php5-fpm', 'server-side HTML-embedded scripting language (FPM-CGI binary)'),
    ('php5-gdcm', 'Grassroots DICOM PHP5 bindings'),
    ('php5-gearman', 'PHP wrapper to libgearman'),
    ('php5-geoip', 'GeoIP module for php5'),
    ('php5-geos', 'GEOS bindings for PHP'),
    ('php5-gmp', 'GMP module for php5'),
    ('php5-gnupg', 'wrapper around the gpgme library'),
    ('php5-igbinary', 'igbinary extension'),
    ('php5-imagick', 'Provides a wrapper to the ImageMagick library'),
    ('php5-imap', 'IMAP module for php5'),
    ('php5-interbase', 'interbase/firebird module for php5'),
    ('php5-intl', 'internationalisation module for php5'),
    ('php5-lasso', 'Library for Liberty Alliance and SAML protocols - PHP 5 bindings'),
    ('php5-librdf', 'PHP5 language bindings for the Redland RDF library'),
    ('php5-libvirt-php', 'libvirt bindings for PHP'),
    ('php5-mapscript', 'php5-cgi module for MapServer'),
    ('php5-mcrypt', 'MCrypt module for php5'),
    ('php5-memcache', 'memcache extension module for PHP5'),
    ('php5-memcached', 'memcached extension module for PHP5, uses libmemcached'),
    ('php5-mongo', 'MongoDB database driver'),
    ('php5-msgpack', 'PHP extension for interfacing with MessagePack'),
    ('php5-mysqlnd-ms', 'MySQL replication and load balancing module for PHP'),
    ('php5-oauth', 'OAuth 1.0 consumer and provider extension'),
    ('php5-odbc', 'ODBC module for php5'),
    ('php5-pecl-http', 'pecl_http module for PHP 5 Extended HTTP Support'),
    ('php5-pecl-http-dev', 'pecl_http module for PHP 5 Extended HTTP Support development headers'),
    ('php5-pgsql', 'PostgreSQL module for php5'),
    ('php5-phpdbg', 'server-side, HTML-embedded scripting language (PHPDBG binary)'),
    ('php5-pinba', 'Pinba module for PHP 5'),
    ('php5-propro', 'propro module for PHP 5'),
    ('php5-propro-dev', 'propro module for PHP 5 development headers'),
    ('php5-pspell', 'pspell module for php5'),
    ('php5-radius', 'PECL radius module for PHP 5'),
    ('php5-raphf', 'raphf module for PHP 5'),
    ('php5-raphf-dev', 'raphf module for PHP 5 development headers'),
    ('php5-recode', 'recode module for php5'),
    ('php5-redis', 'PHP extension for interfacing with Redis'),
    ('php5-remctl', 'PECL module for Kerberos-authenticated command execution'),
    ('php5-rrd', 'PHP bindings to rrd tool system'),
    ('php5-sasl', 'Cyrus SASL Extension'),
    ('php5-snmp', 'SNMP module for php5'),
    ('php5-solr', 'solr module for PHP 5'),
    ('php5-ssh2', 'Bindings for the libssh2 library'),
    ('php5-stomp', 'Streaming Text Oriented Messaging Protocol (STOMP) client module for PHP 5'),
    ('php5-svn', 'PHP Bindings for the Subversion Revision control system'),
    ('php5-sybase', 'Sybase / MS SQL Server module for php5'),
    ('php5-tidy', 'tidy module for php5'),
    ('php5-tokyo-tyrant', 'PHP interface to Tokyo Cabinet''s network interface, Tokyo Tyrant'),
    ('php5-twig', 'Enhance performance of the Twig template engine'),
    ('php5-uprofiler', 'hierarchical profiler for PHP (extension)'),
    ('php5-vtkgdcm', 'Grassroots DICOM VTK PHP bindings'),
    ('php5-xcache', 'Fast, stable PHP opcode cacher'),
    ('php5-xdebug', 'Xdebug Module for PHP 5'),
    ('php5-xhprof', 'Hierarchical Profiler for PHP5'),
    ('php5-xmlrpc', 'XML-RPC module for php5'),
    ('php5-xsl', 'XSL module for php5'),
    ('php5-yac', 'YAC (Yet Another Cache) for PHP 5'),
    ('php5-zmq', 'ZeroMQ messaging'),
]


def populate_php_lib(apps, schema_editor):
    PHPLib = apps.get_model('apimws', 'PHPLib')
    for values in php_lib_values:
        PHPLib.objects.create(name=values[0], description=values[1])


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0041_auto_20150916_1630'),
        ('apimws', '0007_auto_20150917_1056'),
    ]

    operations = [
        migrations.CreateModel(
            name='PHPLib',
            fields=[
                ('name', models.CharField(max_length=150, serialize=False, primary_key=True)),
                ('description', models.CharField(max_length=250)),
                ('available', models.BooleanField(default=True)),
                ('services', models.ManyToManyField(related_name='php_libs', to='sitesmanagement.Service', blank=True)),
            ],
        ),
        migrations.RunPython(populate_php_lib),
    ]
