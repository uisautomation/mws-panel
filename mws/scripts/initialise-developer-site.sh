cd /usr/src/app
./manage.py migrate
./manage.py collectstatic --noinput
./manage.py loaddata mwsauth/fixtures/bjh21_test_users.yaml
./manage.py loaddata apimws/fixtures/phplibs.yaml
./manage.py loaddata apimws/fixtures/apache_modules.yaml
./manage.py loaddata sitesmanagement/fixtures/test_server_IPs.yaml
./manage.py shell <<EOL
from django.contrib.auth.models import User
u = User.objects.get(username='test0001')
u.is_superuser = True
u.is_active = True
u.is_staff = True
u.save()
EOL
