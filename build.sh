#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate

if [ "$CREATE_SUPERUSER" ]; then
  python manage.py createsuperuser --no-input || true
  python manage.py shell -c "from django.contrib.auth import get_user_model; U = get_user_model(); u = U.objects.filter(username='admin').first(); u.set_password('admin1234'); u.save()" || true
fi