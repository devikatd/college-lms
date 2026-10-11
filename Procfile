web: gunicorn lms_core.wsgi:application --bind 0.0.0.0:$PORT
release: python manage.py migrate && python manage.py seed_academic_data
