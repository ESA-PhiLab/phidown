# Makefile for phidown project

# Configuration variables
PYTHON_VERSION ?= 3.11
UV ?= uv
PYTEST_ARGS ?= -q

# Phony targets
.PHONY: all check_uv venv install install_deps dev test clean build activate help

# Default target sets up the project environment
all: install
	@echo "✅ Installation complete."
	@echo "🔄 Run commands with: uv run <command>"

# Display help information
help:
	@echo "📋 Phidown Makefile Targets:"
	@echo "    all         - Set up environment and install dependencies"
	@echo "    venv        - Create uv virtual environment"
	@echo "    install     - Sync project dependencies using uv"
	@echo "    install_deps- Alias for install"
	@echo "    dev         - Sync development and test dependencies"
	@echo "    test        - Run tests with uv"
	@echo "    clean       - Remove uv virtual environment"
	@echo "    activate    - Show instructions to activate environment"
	@echo "    build       - Build source and wheel distributions"
	@echo "    help        - Show this help message"

# Check if uv is available
check_uv:
	@command -v $(UV) >/dev/null 2>&1 || { \
		echo "❌ Error: uv not found. Please install uv first."; \
		echo "   Visit: https://docs.astral.sh/uv/getting-started/installation/"; \
		exit 1; \
	}
	@$(UV) --version >/dev/null || { \
		echo "❌ Error: uv command not working."; \
		exit 1; \
	}

# Create uv virtual environment
venv: check_uv
	@echo "🔧 Creating uv virtual environment with Python $(PYTHON_VERSION)..."
	@$(UV) venv --allow-existing --python $(PYTHON_VERSION) || \
		(echo "❌ Failed to create uv virtual environment"; exit 1)
	@echo "✅ uv virtual environment created successfully"

# Activation instructions
activate: check_uv
	@echo "ℹ️ To activate the uv environment, run: source .venv/bin/activate"
	@echo "  Alternatively, run commands with: uv run <command>"

# Install project dependencies
install: check_uv
	@echo "📚 Syncing project dependencies with uv..."
	@$(UV) sync --locked --python $(PYTHON_VERSION) || \
		(echo "❌ Failed to sync dependencies"; exit 1)
	@echo "✅ Dependencies synced successfully"

# Backward-compatible alias for the previous target name
install_deps: install

# Install development dependencies
dev: check_uv
	@echo "🛠️ Syncing development and test dependencies with uv..."
	@$(UV) sync --locked --python $(PYTHON_VERSION) --extra dev --extra test || \
		(echo "❌ Failed to sync development dependencies"; exit 1)
	@echo "✅ Development dependencies synced successfully"

# Run tests
test: check_uv
	@echo "🧪 Running tests with uv..."
	@$(UV) run --locked --python $(PYTHON_VERSION) --extra test pytest $(PYTEST_ARGS) || \
		(echo "❌ Tests failed"; exit 1)

# Clean the uv virtual environment
clean:
	@echo "🧹 Removing uv virtual environment..."
	@rm -rf .venv || \
		(echo "❌ Failed to remove uv virtual environment"; exit 1)
	@echo "✅ uv virtual environment has been removed."

# Build source and wheel distributions
build: check_uv
	@echo "📦 Building sdist and wheel..."
	@$(UV) build --python $(PYTHON_VERSION) || \
		(echo "❌ Build failed"; exit 1)
	@echo "✅ Build complete. Distributions are in the dist/ directory."
