.PHONY: help setup venv install test lint format run run-module docker-build docker-run docker-stop docker-logs ghcr-pull ghcr-up ghcr-down ghcr-logs clean pre-commit pre-commit-run

# Default Python executable and virtual environment path
PYTHON := python3
VENV := .venv
VENV_PYTHON := $(VENV)/bin/python
VENV_PIP := $(VENV)/bin/pip

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

venv: ## Create a virtual environment
	$(PYTHON) -m venv $(VENV)
	@echo "Virtual environment created in $(VENV). Activate with 'source $(VENV)/bin/activate'"

setup: venv ## Set up the development environment
	$(VENV_PIP) install --upgrade pip
	$(VENV_PIP) install -r requirements.txt
	@echo "Setup complete"

install: ## Install dependencies in the active environment
	pip install -r requirements.txt

test: ## Run tests with pytest
	$(VENV_PYTHON) -m pytest -v plex_announcer/tests/

test-cov: ## Run tests with coverage report
	$(VENV_PYTHON) -m pytest --cov=plex_announcer --cov-report=term plex_announcer/tests/

lint: ## Check code style with flake8
	$(VENV_PYTHON) -m flake8 plex_announcer/ *.py

format: ## Format code with black
	$(VENV_PYTHON) -m black plex_announcer/ *.py

run: ## Run the Discord bot locally
	$(VENV_PYTHON) run.py

run-module: ## Run the Discord bot directly as a module
	$(VENV_PYTHON) -m plex_announcer

pre-commit: ## Install pre-commit hooks
	$(VENV_PYTHON) -m pip install pre-commit
	$(VENV_PYTHON) -m pre-commit install

pre-commit-run: ## Run pre-commit hooks on all files
	$(VENV_PYTHON) -m pre-commit run --all-files

# Docker commands
docker-build: ## Build the Docker image
	docker-compose build

docker-up: ## Run the Docker container
	docker-compose up -d

docker-down: ## Stop the Docker container
	docker-compose down

docker-logs: ## View Docker container logs
	docker-compose logs -f

# GitHub Container Registry commands
ghcr-pull: ## Pull the Docker image from GitHub Container Registry
	docker-compose -f docker-compose.deploy.yml pull

ghcr-up: ## Run the Docker container from GitHub Container Registry
	docker-compose -f docker-compose.deploy.yml up -d

ghcr-down: ## Stop the Docker container from GitHub Container Registry
	docker-compose -f docker-compose.deploy.yml down

ghcr-logs: ## View Docker container logs from GitHub Container Registry
	docker-compose -f docker-compose.deploy.yml logs -f

# Clean up
clean: ## Remove virtual environment and cache files
	rm -rf $(VENV) __pycache__ .pytest_cache .coverage
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf htmlcov
