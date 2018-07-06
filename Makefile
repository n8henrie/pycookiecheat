GREP := $(shell command -v ggrep || command -v grep)
SED := $(shell command -v gsed || command -v sed)

.PHONY: clean-pyc clean-build clean clean-test update-reqs lint test test-all release dist

help:
	@echo "clean - remove all build, test, coverage and Python artifacts"
	@echo "clean-build - remove build artifacts"
	@echo "clean-pyc - remove Python file artifacts"
	@echo "clean-test - remove test and coverage artifacts"
	@echo "lint - check style with flake8"
	@echo "test - run tests quickly with the default Python"
	@echo "test-all - run tests on every Python version with tox"
	@echo "release - package and upload a release"
	@echo "dist - package"
	@echo "update-reqs - try to update dependencies"

clean: clean-build clean-pyc clean-test

clean-build:
	rm -fr build/
	rm -fr dist/
	rm -fr *.egg-info
	rm -fr src/*.egg-info

clean-pyc:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

clean-test:
	rm -fr .tox/
	rm -f .coverage
	rm -fr htmlcov/

lint:
	flake8 pycookiecheat tests

test:
	py.test tests

test-all:
	tox

release: dist
	twine upload dist/*

dist: clean
	python3 setup.py sdist
	python3 setup.py bdist_wheel
	ls -l dist

update-reqs: requirements.txt
	@$(GREP) --invert-match --no-filename '^#' requirements*.txt | \
		$(SED) 's|==.*$$||g' | \
		xargs ./.venv/bin/python -m pip install --upgrade; \
	for reqfile in requirements*.txt; do \
		echo "Updating $${reqfile}..."; \
		./.venv/bin/python -c 'print("\n{:#^80}".format("  Updated reqs below  "))' >> "$${reqfile}"; \
		for lib in $$(./.venv/bin/pip freeze --all --isolated --quiet | $(GREP) '=='); do \
			if $(GREP) "^$${lib%%=*}==" "$${reqfile}" >/dev/null; then \
				echo "$${lib}" >> "$${reqfile}"; \
			fi; \
		done; \
	done;
