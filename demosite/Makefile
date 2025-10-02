LANGUAGES:=`find ./medspeak/locale/ -mindepth 1 -maxdepth 1 -type d -printf "--locale %f "`
MANAGE = ./manage.py

MANAGE:="django-admin"
LANGUAGES:=`find ./locale/ -mindepth 1 -maxdepth 1 -type d -printf "--locale %f "`

update:
	git pull
	$(MANAGE) tetrabuild
	$(MANAGE) collectstatic --noinput
	supervisorctl restart tetra


localecompile:
	$(MANAGE) compilemessages

localegen:
    # don't --keep-pot
	$(MANAGE) makemessages --ignore "build/*" $(LANGUAGES)


locale: localegen localecompile


localegen:
    # don't --keep-pot
	$(MANAGE) makemessages --ignore "static/*"  --ignore "build/*" $(LANGUAGES)
	$(MANAGE) makemessages -d djangojs --ignore "static/*" --ignore "build/*" $(LANGUAGES)

localecompile:
	$(MANAGE) compilemessages
