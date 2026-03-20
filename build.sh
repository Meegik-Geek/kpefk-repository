#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate

if [ "$CREATE_SUPERUSER" ]; then
  python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
u, created = User.objects.get_or_create(username='admin')
u.email = 'admin@example.com'
u.is_active = True
User.objects.filter(pk=u.pk).update(is_staff=True, is_superuser=True)
u.set_password('Kpefk@2024!')
User.objects.filter(pk=u.pk).update(password=u.password)
from home.models import UserProfile
UserProfile.objects.filter(user=u).update(role='admin')
print('Done')
"
fi