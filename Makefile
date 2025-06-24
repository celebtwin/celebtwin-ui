.PHONY: help
help:
	@echo "make setup        - creates the virtual env and install packages"
	@echo "make lint         - run code analysis and style checks"
	@echo "make requirements - install requirements"
	@echo "make pip-compile  - compile requirements files"
	@echo "make streamlit    - run local streamlit app"

PYTHON = python3
PY_VERSION = 3.12.9
PROJECT = celebtwin-ui

.PHONY: setup
setup:
	pyenv local --unset
	pyenv install --skip-existing $(PY_VERSION)
	pyenv virtualenvs --bare | grep -e '^$(PROJECT)$$' \
	|| pyenv virtualenv $(PY_VERSION) $(PROJECT)
	pyenv local $(PROJECT)
	$(MAKE) requirements

.PHONY: lint
lint:
	-ruff check app.py celebtwin_ui
	-mypy app.py celebtwin_ui

.PHONY: streamlit
streamlit:
	streamlit run app.py

.PHONY: requirements
requirements: pip-compile
	pip install --quiet -r requirements.txt -r requirements-dev.txt

.PHONY: pip-compile
pip-compile: requirements.txt requirements-dev.txt

PIP_COMPILE_FLAGS = --quiet --strip-extras --generate-hashes --allow-unsafe

requirements.txt: pyproject.toml
	pip-compile $(PIP_COMPILE_FLAGS) $<

# Extract dev dependencies from pyproject.toml
EXTRACT_DEV_REQS = $(PYTHON) -c "import tomllib; print('\n'.join(tomllib.load(open('pyproject.toml', 'rb'))['project']['optional-dependencies']['dev']))"

requirements-dev.txt: pyproject.toml requirements.txt
	$(EXTRACT_DEV_REQS) > requirements-dev.in
	pip-compile $(PIP_COMPILE_FLAGS) --constraint=requirements.txt \
	requirements-dev.in
	rm requirements-dev.in

clean:
	@rm -fr */__pycache__
	@rm -fr build
	@rm -fr dist
	@rm -fr *.dist-info
	@rm -fr *.egg-info
	@rm requirements-dev.in
