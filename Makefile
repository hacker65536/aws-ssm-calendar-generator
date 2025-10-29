# AWS SSM Calendar ICS Generator - Development Makefile

.PHONY: help install install-dev test test-unit test-integration test-e2e lint format type-check security-check quality-check clean build docs

# Default target
help:
	@echo "AWS SSM Calendar ICS Generator - Development Commands"
	@echo ""
	@echo "Setup Commands:"
	@echo "  install          Install production dependencies"
	@echo "  install-dev      Install development dependencies"
	@echo "  setup-pre-commit Setup pre-commit hooks"
	@echo ""
	@echo "Testing Commands:"
	@echo "  test             Run all tests"
	@echo "  test-unit        Run unit tests only"
	@echo "  test-integration Run integration tests only"
	@echo "  test-e2e         Run end-to-end tests only"
	@echo "  test-coverage    Run tests with coverage report"
	@echo ""
	@echo "Code Quality Commands:"
	@echo "  lint             Run all linting checks"
	@echo "  format           Format code with black and isort"
	@echo "  type-check       Run mypy type checking"
	@echo "  security-check   Run security checks with bandit and safety"
	@echo "  quality-check    Run all quality checks (lint + type + security)"
	@echo ""
	@echo "Build Commands:"
	@echo "  clean            Clean build artifacts"
	@echo "  build            Build package"
	@echo "  docs             Generate documentation"
	@echo ""
	@echo "Development Commands:"
	@echo "  run-example      Run example usage"
	@echo "  debug            Run with debug logging"

# Installation commands
install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"

setup-pre-commit:
	pre-commit install
	pre-commit install --hook-type commit-msg

# Testing commands
test:
	pytest

test-unit:
	pytest tests/unit/ -v

test-integration:
	pytest tests/integration/ -v

test-e2e:
	pytest tests/integration/test_end_to_end.py -v

test-coverage:
	pytest --cov=src --cov-report=html --cov-report=term-missing

test-watch:
	pytest-watch -- tests/

# Code quality commands
lint:
	@echo "Running flake8..."
	flake8 src/ tests/
	@echo "Running pydocstyle..."
	pydocstyle src/ --convention=google
	@echo "Linting completed successfully!"

format:
	@echo "Running black..."
	black src/ tests/
	@echo "Running isort..."
	isort src/ tests/
	@echo "Code formatting completed!"

format-check:
	@echo "Checking black formatting..."
	black --check src/ tests/
	@echo "Checking isort formatting..."
	isort --check-only src/ tests/

type-check:
	@echo "Running mypy type checking..."
	mypy src/
	@echo "Type checking completed successfully!"

security-check:
	@echo "Running bandit security check..."
	bandit -r src/ -c .bandit
	@echo "Running safety dependency check..."
	safety check
	@echo "Security checks completed successfully!"

quality-check: format-check lint type-check security-check
	@echo "All quality checks passed!"

# Pre-commit commands
pre-commit-all:
	pre-commit run --all-files

pre-commit-update:
	pre-commit autoupdate

# Build commands
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

build: clean
	python -m build

build-wheel:
	python -m build --wheel

build-sdist:
	python -m build --sdist

# Documentation commands
docs:
	@echo "Generating API documentation..."
	mkdir -p docs/api/
	python -c "
import src.japanese_holidays
import src.ics_generator
import src.calendar_analyzer
import src.aws_client
import src.config
print('API documentation would be generated here')
"

# Development commands
run-example:
	python -m src.cli holidays --year 2024

run-export-example:
	python -m src.cli export --output example_holidays.ics --include-holidays --holidays-year 2024

debug:
	python -m src.cli --verbose holidays --year 2024

# CI/CD simulation
ci-test: install-dev quality-check test-coverage
	@echo "CI pipeline simulation completed successfully!"

# Performance testing
perf-test:
	python -m pytest tests/ -k "not slow" --benchmark-only

# Dependency management
update-deps:
	pip-compile requirements.in
	pip-compile requirements-dev.in

check-deps:
	pip-check

# Docker commands (if needed)
docker-build:
	docker build -t aws-ssm-calendar-generator .

docker-test:
	docker run --rm aws-ssm-calendar-generator pytest

# Release commands
release-check: clean quality-check test build
	@echo "Release check completed successfully!"
	@echo "Ready for release!"

release-test:
	python -m twine check dist/*

# Environment setup
setup-dev-env: install-dev setup-pre-commit
	@echo "Development environment setup completed!"
	@echo "Run 'make test' to verify everything is working."

# Quick development cycle
dev: format lint test-unit
	@echo "Quick development cycle completed!"

# Full validation (for CI)
validate: install-dev format-check lint type-check security-check test-coverage
	@echo "Full validation completed successfully!"