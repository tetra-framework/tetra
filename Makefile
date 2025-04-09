
venv:
	# Create venv if it doesn't exist
	test -d .venv || /usr/bin/env python3 -m venv .venv

_activate:
	. .venv/bin/activate

npm:
	cd tests && test -d node_modules || npm install

test: venv _activate npm
	cd tests && python -m pytest

#coverage:
#	coverage run -m pytest

check: venv _activate
	ruff check .

doc: venv _activate
	mkdocs build -d docs/build/doc/

doc-dev: venv _activate
	mkdocs serve -a localhost:8002

build: venv _activate npm
	# remove dist/ if it exists
	rm -rf dist/
	python -m build

# https://packaging.python.org/en/latest/tutorials/packaging-projects/#uploading-your-project-to-pypi
publish-test:
	python -m twine upload --repository testpypi dist/*

publish-prod:
	python -m twine upload --repository pypi dist/*