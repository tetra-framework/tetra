
test:
	pytest

#coverage:
#	coverage run -m pytest

check:
	ruff check .

doc:
	cd docs
	mkdocs build -d build/doc/

doc-dev:
	cd docs
	mkdocs serve

build:
	python -m build

