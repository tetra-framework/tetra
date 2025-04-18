update:
	git pull
	./manage.py tetrabuild
	./manage.py collectstatic --noinput
	supervisorctl restart tetra