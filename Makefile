.PHONY: clean clean-test clean-pyc clean-build docs help
.DEFAULT_GOAL := help

define PRINT_HELP_PYSCRIPT
import re, sys

for line in sys.stdin:
	match = re.match(r'^([a-zA-Z_-]+):.*?## (.*)$$', line)
	if match:
		target, help = match.groups()
		print("%-20s %s" % (target, help))
endef
export PRINT_HELP_PYSCRIPT

help:
	@python3 -c "$$PRINT_HELP_PYSCRIPT" < $(MAKEFILE_LIST)

clean: clean-build clean-pyc clean-test ## remove all build, test, coverage and Python artifacts

clean-build: ## remove build artifacts
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -exec rm -f {} +

clean-pyc: ## remove Python file artifacts
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

clean-test: ## remove test and coverage artifacts
	rm -fr .tox/
	rm -f .coverage
	rm -fr htmlcov/
	rm -fr .pytest_cache

lint: ## check style with ruff
	ruff src tests

format: ## Run code formatter: black and isort
	@echo "(isort) Ordering imports..."
	@isort --profile black src tests
	@echo "(black) Formatting codebase..."
	@black --config black.toml src tests
	@echo "(black) Formatting stubs..."
	@find src -name "*.pyi" ! -name "*_pb2*" -exec black --pyi --config black.toml {} \;
	@echo "(ruff) Running fix only..."
	@ruff check src tests --fix-only

test: ## run tests quickly with the default Python
	pytest

test-all: ## run tests on every Python version with tox
	tox

coverage: ## check code coverage quickly with the default Python
	coverage run --source src -m pytest
	coverage report -m
	coverage html

docs: ## generate Sphinx HTML documentation, including API docs
	sphinx-apidoc -o docs/source src
	$(MAKE) -C docs clean
	$(MAKE) -C docs html

servedocs: docs ## compile the docs watching for changes
	watchmedo shell-command -p '*.rst' -c '$(MAKE) -C docs html' -R -D .

release: dist ## package and upload a release
	twine upload dist/*

dist: clean ## builds source and wheel package
	python setup.py sdist
	python setup.py bdist_wheel
	ls -l dist

install: clean ## install the package to the active Python's site-packages
	python setup.py install

dev-install: clean ## install the package in editable mode
	pip install -e .

requirements: ## install the requirements
	pip install -r requirements.txt

bump-major: ## bump major version
	bump2version major

bump-minor: ## bump minor version
	bump2version minor

bump-patch: ## bump patch version
	bump2version patch
