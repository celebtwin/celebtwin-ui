.PHONY: help
help:
	@echo "make setup        - creates the virtual env and install packages"
	@echo "make lint         - run code analysis and style checks"
	@echo "make requirements - install requirements"
	@echo "make pip-compile  - compile requirements files"
	@echo "make streamlit    - run local streamlit app"

PY_VERSION=3.12.9
PROJECT=celebtwin-ui

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
	-ruff check celebtwin
	-mypy celebtwin

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

requirements-dev.txt: requirements-dev.in requirements.txt
	pip-compile $(PIP_COMPILE_FLAGS) --constraint=requirements.txt $<

clean:
	@rm -fr */__pycache__
	@rm -fr build
	@rm -fr dist
	@rm -fr *.dist-info
	@rm -fr *.egg-info
