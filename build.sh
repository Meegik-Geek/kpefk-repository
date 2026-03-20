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
u.is_superuser = True
u.is_staff = True
u.is_active = True
u.set_password('Kpefk@2024!')
u.save()
print('Done. is_superuser:', u.is_superuser)
"
fi