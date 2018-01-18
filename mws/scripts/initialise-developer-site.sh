cd /usr/src/app
./manage.py migrate
./manage.py collectstatic --noinput
./manage.py loaddata mwsauth/fixtures/bjh21_test_users.yaml
./manage.py loaddata apimws/fixtures/phplibs.yaml
./manage.py shell <<EOL
from django.contrib.auth.models import User
from sitesmanagement.tests.tests import pre_create_site
u = User.objects.get(username='test0001')
u.is_superuser = True
u.is_active = True
u.is_staff = True
u.save()
pre_create_site()
EOL
