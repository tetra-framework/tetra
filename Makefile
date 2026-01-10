
setup:
	# Create venv if it doesn't exist
	pip install -U pip uv
	uv sync

setup-dev:
	pip install -U pip uv
	uv sync --extra dev
	playwright install

npm:
	cd tests &&	test -d node_modules || npm install

test: npm
	uv run pytest tests

#coverage:
#	coverage run -m pytest

check:
	uvx ruff check

doc:
	uv sync --extra doc
	mkdocs build -d docs/build/doc/

doc-dev:
	uv sync --extra doc
	mkdocs serve -a localhost:8002

build-js:
	scripts/build_js.sh

build: npm build-js
	rm -rf ./dist/
	uv build

# https://packaging.python.org/en/latest/tutorials/packaging-projects/#uploading-your-project-to-pypi
publish:
	uv publish

