
venv:
	# Create venv if it doesn't exist
	test -d .venv || python3 -m venv .venv

npm: venv
	cd tests && test -d node_modules || npm install

_activate:
	. .venv/bin/activate

test: venv _activate npm
	cd tests && python -m pytest

#coverage:
#	coverage run -m pytest

check: venv _activate
	ruff check .

doc: venv _activate
	mkdocs build -d docs/build/doc/

doc-dev: venv _activate
	mkdocs serve

build: venv _activate npm
	python -m build

# https://packaging.python.org/en/latest/tutorials/packaging-projects/#uploading-your-project-to-pypi
publish-test: build
	python -m twine upload --repository testpypi dist/*

publish-prod: build
	python -m twine upload --repository pypi dist/*