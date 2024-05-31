# Project Configuration
PROJECT_NAME := $(shell basename $(CURDIR))
VIRTUAL_ENVIRONMENT := $(CURDIR)/.venv
LOCAL_PYTHON := $(VIRTUAL_ENVIRONMENT)/bin/python3

# Help documentation
define HELP
Manage $(PROJECT_NAME). Usage:

make run        - Run $(PROJECT_NAME).
make install    - Create virtual environment & install dependencies.
make update     - Update pip dependencies via Poetry and output requirements.txt.
make format     - Format code with Python's Black library.
make lint       - Check code formatting with flake8.
make clean      - Remove cached files and lock files.
endef
export HELP

# Phony targets
.PHONY: run install update format lint clean help

# Ensure virtual environment exists
env: $(LOCAL_PYTHON)

# Display help
all help:
	@echo "$$HELP"

# Install dependencies
install: $(LOCAL_PYTHON)
	. $(VIRTUAL_ENVIRONMENT)/bin/activate
	$(LOCAL_PYTHON) -m pip install --upgrade pip setuptools wheel
	$(LOCAL_PYTHON) -m pip install -r requirements.txt

# Run the project
run: env
	. $(VIRTUAL_ENVIRONMENT)/bin/activate && flask run

# Update dependencies
update: $(LOCAL_PYTHON)
	$(LOCAL_PYTHON) -m pip install --upgrade pip setuptools wheel
	poetry update
	poetry export -f requirements.txt --output requirements.txt --without-hashes

# Format the code
format: env
	isort --multi-line=3 .
	black .

# Lint the code
lint:
	flake8 . --count \
		--select=E9,F63,F7,F82 \
		--exclude .git,.github,__pycache__,.pytest_cache,.venv,logs,creds,docs \
		--show-source \
		--statistics

# Clean cached and unnecessary files
clean:
	find . -name '*.pyc' -delete
	find . -name '__pycache__' -delete
	find . -name 'poetry.lock' -delete
	find . -name 'Pipfile.lock' -delete
	find . -name '*.log' -delete
	find . -wholename 'logs/*.json' -delete
	find . -wholename '.pytest_cache' -delete
	find . -wholename '**/.pytest_cache' -delete
	find . -wholename '**/.webassets-cache' -delete
	find . -wholename './logs' -delete

# Create virtual environment if it does not exist
$(LOCAL_PYTHON):
	if [ ! -d "$(VIRTUAL_ENVIRONMENT)" ]; then python3 -m venv $(VIRTUAL_ENVIRONMENT); fi
