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
	pip install --quiet --upgrade pip
	pip install --quiet -r requirements.txt
	pip install --quiet -r requirements-dev.txt

.PHONY: pip-compile
pip-compile: requirements.txt requirements-dev.txt

requirements.txt: requirements.in
	pip-compile --quiet --strip-extras requirements.in

requirements-dev.txt: requirements-dev.in
	pip-compile --quiet --strip-extras --constraint=requirements.txt \
	requirements-dev.in

clean:
	@rm -fr */__pycache__
	@rm -fr build
	@rm -fr dist
	@rm -fr *.dist-info
	@rm -fr *.egg-info
