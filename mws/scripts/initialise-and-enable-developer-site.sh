cd /usr/src/app
./scripts/initialise-developer-site.sh
./manage.py shell <<EOL
from django.contrib.auth.models import User
import uuid
import datetime
from sitesmanagement.models import EmailConfirmation, Site
site = Site.objects.first()
site.disabled = False
site.start_date = datetime.date.today()
site.email = 'test0001@cam.ac.uk'
site.save()
site.users.add(User.objects.get(username="test0001"))
EmailConfirmation.objects.create(email=site.email, token=uuid.uuid4(), status="accepted", site=site)
EOL
