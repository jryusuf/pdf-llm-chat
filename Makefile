.PHONY: all setup-dev install-dev run-server test clean

VENV_DIR := venv
PYTHON := $(VENV_DIR)/bin/python
PIP := $(VENV_DIR)/bin/pip
UVICORN := $(VENV_DIR)/bin/uvicorn
PYTEST := $(VENV_DIR)/bin/pytest
BEHAVE := $(VENV_DIR)/bin/behave
BEHAVE_ACCOUNT := $(VENV_DIR)/bin/behave app/account/tests/features
BEHAVE_CHAT := $(VENV_DIR)/bin/behave app/chat/tests/features
BEHAVE_PDF := $(VENV_DIR)/bin/behave app/pdf/tests/features

# Default target
all: setup-dev install-dev

# Create virtual environment if it doesn't exist
setup-dev: $(VENV_DIR)/bin/activate

$(VENV_DIR)/bin/activate:
	@echo "Creating virtual environment in $(VENV_DIR)..."
	python3 -m venv $(VENV_DIR)
	@echo ""
	@echo "Virtual environment created."
	@echo "To activate it, run: source $(VENV_DIR)/bin/activate"
	@echo "Then run 'make install-dev' to install dependencies."

# Install development dependencies
install-dev: $(VENV_DIR)/bin/activate
	@echo "Installing development dependencies..."
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements-dev.txt
	@echo "Development dependencies installed."

# Run the FastAPI server with Uvicorn
run-server: $(VENV_DIR)/bin/activate
	@echo "Starting FastAPI server with Uvicorn..."
	$(UVICORN) app.main:app --host 0.0.0.0 --port 8000 --reload

# Run tests (both pytest and behave)
test: $(VENV_DIR)/bin/activate
	@echo "Running pytest tests..."
	$(PYTEST) --cov=app --cov-report=term-missing
	@echo "\nRunning behave tests..."
	$(BEHAVE)
	@echo "\nRunning account service behave tests..."
	$(BEHAVE_ACCOUNT)
	@echo "\nRunning pdf service behave tests..."
	$(BEHAVE_PDF)
	@echo "\nRunning chat service behave tests..."
	$(BEHAVE_CHAT)

# Clean up virtual environment and __pycache__ directories
clean:
	@echo "Cleaning up..."
	rm -rf $(VENV_DIR)
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".coverage" -exec rm -rf {} +
	@echo "Cleanup complete."
