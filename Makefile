PYTHON := .venv/bin/python

.PHONY: help install run test lint check clean

help:
	@echo "make install  Create .venv and install development dependencies"
	@echo "make run      Start the API on http://localhost:8000"
	@echo "make test     Run tests"
	@echo "make lint     Run ruff"
	@echo "make check    Lint, compile source files and run tests"
	@echo "make clean    Remove generated caches and local databases"

install:
	python3 -m venv .venv
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r requirements-dev.txt

run:
	cd src && ../$(PYTHON) -m uvicorn main:app --reload

test:
	$(PYTHON) -m pytest -q

lint:
	$(PYTHON) -m ruff check .

check: lint
	$(PYTHON) -m compileall -q src tests
	$(PYTHON) -m pytest -q

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -rf .pytest_cache .coverage htmlcov
	find . -name 'blog_engine*.db' -delete
