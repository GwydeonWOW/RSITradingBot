.PHONY: setup test run migrate docker-up docker-down lint clean help

PYTHON ?= python3
PIP ?= pip3
DOCKER ?= docker

BACKEND_DIR := backend
VENV_DIR := backend/.venv

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

setup: ## Create virtual environment and install dependencies
	$(PYTHON) -m venv $(VENV_DIR)
	$(VENV_DIR)/bin/pip install --upgrade pip
	$(VENV_DIR)/bin/pip install -r $(BACKEND_DIR)/requirements.txt

test: ## Run all tests with coverage
	cd $(BACKEND_DIR) && $(VENV_DIR)/bin/pytest tests/ -v --tb=short --cov=app --cov-report=term-missing

test-rsi: ## Run RSI engine tests only
	cd $(BACKEND_DIR) && $(VENV_DIR)/bin/pytest tests/test_rsi_engine.py -v

test-core: ## Run all core module tests
	cd $(BACKEND_DIR) && $(VENV_DIR)/bin/pytest tests/test_rsi_engine.py tests/test_regime.py tests/test_signal.py tests/test_backtester.py -v

run: ## Start the development server
	cd $(BACKEND_DIR) && $(VENV_DIR)/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

migrate: ## Run database migrations
	cd $(BACKEND_DIR) && $(VENV_DIR)/bin/alembic upgrade head

migrate-create: ## Create a new migration (usage: make migrate-create msg="description")
	cd $(BACKEND_DIR) && $(VENV_DIR)/bin/alembic revision --autogenerate -m "$(msg)"

docker-up: ## Start all services via Docker Compose
	$(DOCKER) compose up -d --build

docker-down: ## Stop all Docker Compose services
	$(DOCKER) compose down

docker-logs: ## Tail logs from all services
	$(DOCKER) compose logs -f

docker-psql: ## Connect to PostgreSQL
	$(DOCKER) compose exec postgres psql -U rsi_user -d rsi_trading

docker-redis: ## Connect to Redis CLI
	$(DOCKER) compose exec redis redis-cli

lint: ## Run linters
	cd $(BACKEND_DIR) && $(VENV_DIR)/bin/python -m flake8 app/ tests/ --max-line-length=120

clean: ## Remove generated files
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf backend/.pytest_cache backend/.mypy_cache backend/htmlcov backend/.coverage
