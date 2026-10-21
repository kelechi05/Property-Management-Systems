pip install -r requirements.txt

pyhton manage.py collectstatic --noinput

python manage.py migrate
