# Makefile for phidown project

# Configuration variables
PYTHON_VERSION := 3.11
PDM_EXE := $(shell which pdm || echo "pdm")

# Phony targets
.PHONY: all venv install_deps dev test clean build help

# Default target shows help
all: venv install_deps
	@echo "✅ Installation complete."
	@echo "🔄 Please activate the environment: pdm shell"

# Display help information
help:
	@echo "📋 Phidown Makefile Targets:"
	@echo "    all         - Set up environment and install dependencies"
	@echo "    venv        - Create PDM virtual environment"
	@echo "    install_deps- Install project dependencies using PDM"
	@echo "    dev         - Install development dependencies"
	@echo "    test        - Run tests"
	@echo "    clean       - Remove PDM virtual environment"
	@echo "    activate    - Show instructions to activate environment"
	@echo "    build       - Build source and universal wheel distributions"
	@echo "    help        - Show this help message"

# Check if PDM is available
check_pdm:
	@command -v pdm || { \
		echo "❌ Error: PDM not found. Please install PDM first."; \
		echo "   Visit: https://pdm.fming.dev/latest/#installation"; \
		exit 1; \
	}
	@$(PDM_EXE) --version || { \
		echo "❌ Error: PDM command not working."; \
		exit 1; \
	}

# Create PDM virtual environment
venv: check_pdm
	@echo "🔧 Creating PDM virtual environment with Python $(PYTHON_VERSION)..."
	@$(PDM_EXE) venv create --python $(PYTHON_VERSION) || \
		(echo "❌ Failed to create PDM virtual environment"; exit 1)
	@echo "✅ PDM virtual environment created successfully"

# Activation instructions
activate: check_pdm
	@echo "ℹ️ To activate the PDM environment, run: pdm shell"
	@echo "  Alternatively, you can run commands with: pdm run <command>"

# Install project dependencies
install_deps: venv
	@echo "📚 Installing project dependencies with PDM..."
	@$(PDM_EXE) install || \
		(echo "❌ Failed to install dependencies"; exit 1)
	@echo "✅ Dependencies installed successfully"

# Install development dependencies
dev: install_deps
	@echo "🛠️ Installing development dependencies..."
	@$(PDM_EXE) install -G dev || \
		(echo "❌ Failed to install development dependencies"; exit 1)
	@echo "✅ Development dependencies installed successfully"

# Run tests
test:
	@echo "🧪 Running tests..."
	@$(PDM_EXE) run pytest || \
		(echo "❌ Tests failed"; exit 1)

# Clean the PDM virtual environment
clean: check_pdm
	@echo "🧹 Removing PDM virtual environment..."
	@python -m venv remove && rm -rf .venv || \
		(echo "❌ Failed to remove PDM virtual environment"; exit 1)
	@echo "✅ PDM virtual environment has been removed."

# Build source and universal wheel distributions
build:
	@echo "📦 Building sdist and universal wheel..."
	@$(PDM_EXE) build || \
		(echo "❌ Build failed"; exit 1)
	@echo "✅ Build complete. Distributions are in the dist/ directory."
