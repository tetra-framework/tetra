LANGUAGES:=`find ./medspeak/locale/ -mindepth 1 -maxdepth 1 -type d -printf "--locale %f "`
MANAGE = ./manage.py

update:
	git pull
	./manage.py tetrabuild
	./manage.py collectstatic --noinput
	supervisorctl restart tetra


localegen:
    # don't --keep-pot
	$(MANAGE) makemessages --ignore "static/*"  --ignore "build/*" $(LANGUAGES)
	$(MANAGE) makemessages -d djangojs --ignore "static/*" --ignore "build/*" $(LANGUAGES)

localecompile:
	$(MANAGE) compilemessages
