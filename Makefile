
setup:
	# Create venv if it doesn't exist
	pip install -U pip uv
	uv sync

npm:
	test -d node_modules || npm install

test: npm
	python -m pytest

#coverage:
#	coverage run -m pytest

check:
	uvx ruff check

doc:
	mkdocs build -d docs/build/doc/

doc-dev:
	mkdocs serve -a localhost:8002

build-js:
	scripts/build_js.sh

build: npm build-js
	rm -rf ./dist/
	uv build

# https://packaging.python.org/en/latest/tutorials/packaging-projects/#uploading-your-project-to-pypi
publish-prod:
	uv publish
