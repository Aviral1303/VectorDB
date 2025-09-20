# Makefile for Vector DB project

.PHONY: help install run dev test lint format docker-build docker-run clean

# Default target
help:
	@echo "Available commands:"
	@echo "  install      - Install dependencies"
	@echo "  run          - Run the application"
	@echo "  dev          - Run in development mode with reload"
	@echo "  test         - Run tests"
	@echo "  lint         - Run linting (when configured)"
	@echo "  format       - Format code (when configured)"
	@echo "  docker-build - Build Docker image"
	@echo "  docker-run   - Run Docker container"
	@echo "  clean        - Clean up temporary files"

# Install dependencies
install:
	pip install -r requirements.txt

# Run the application
run:
	python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# Run in development mode
dev:
	python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Run tests
test:
	python -m pytest tests/ -v

# Run linting (placeholder for future)
lint:
	@echo "Linting not configured yet"
	# python -m flake8 app/ tests/
	# python -m mypy app/

# Format code (placeholder for future)
format:
	@echo "Formatting not configured yet"
	# python -m black app/ tests/
	# python -m isort app/ tests/

# Build Docker image
docker-build:
	docker build -t vector-db:latest .

# Run Docker container
docker-run:
	docker run -p 8000:8000 --env-file .env vector-db:latest

# Run Docker container in development mode
docker-dev:
	docker build -t vector-db:dev --target development .
	docker run -p 8000:8000 -v $(PWD)/app:/app/app vector-db:dev

# Clean up
clean:
	find . -type d -name "__pycache__" -delete
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name "*.egg-info" -delete
