# Makefile for phidown project

# Configuration variables
ENV_NAME := phidown-env
PYTHON_VERSION := 3.9
CONDA_EXE := $(shell which conda || echo "/usr/bin/env conda")
CONDA_BASE := $(shell $(CONDA_EXE) info --base || echo "$$HOME/anaconda3")

# Phony targets
.PHONY: all env activate install_pdm install_deps dev test clean build help

# Default target shows help
all: env install_pdm install_deps
	@echo "✅ Installation complete."
	@echo "🔄 Please activate the environment: conda activate $(ENV_NAME)"

# Display help information
help:
	@echo "📋 Phidown Makefile Targets:"
	@echo "    all         - Set up environment and install dependencies"
	@echo "    env         - Create conda environment"
	@echo "    install_pdm - Install PDM package manager"
	@echo "    install_deps- Install project dependencies using PDM"
	@echo "    dev         - Install development dependencies"
	@echo "    test        - Run tests"
	@echo "    clean       - Remove conda environment"
	@echo "    activate    - Show instructions to activate environment"
	@echo "    build       - Build source and universal wheel distributions"
	@echo "    help        - Show this help message"

# Check if conda is available
check_conda:
	@command -v conda || { \
		echo "❌ Error: conda not found. Please install conda first."; \
		echo "   Visit: https://docs.conda.io/projects/conda/en/latest/user-guide/install/"; \
		exit 1; \
	}
	@$(CONDA_EXE) --version || { \
		echo "❌ Error: conda command not working. Try initializing it first:"; \
		echo "   For bash: eval \"$$($(shell dirname $(CONDA_EXE))/conda shell.bash hook)\""; \
		echo "   For zsh:  eval \"$$($(shell dirname $(CONDA_EXE))/conda shell.zsh hook)\""; \
		exit 1; \
	}

# Create conda environment
env: check_conda
	@echo "🔧 Creating conda environment $(ENV_NAME) with Python $(PYTHON_VERSION)..."
	@$(CONDA_EXE) create -n $(ENV_NAME) python=$(PYTHON_VERSION) -y || \
		(echo "❌ Failed to create conda environment"; exit 1)
	@echo "✅ Conda environment created successfully"

# Activation instructions
activate: check_conda
	@echo "ℹ️ To activate the conda environment, run: conda activate $(ENV_NAME)"
	@echo "  Alternatively, source the conda.sh script for your shell:"
	@echo "    For bash/zsh: source $(CONDA_BASE)/etc/profile.d/conda.sh"
	@echo "    Then run: conda activate $(ENV_NAME)"

# Install PDM
install_pdm: env
	@echo "📦 Installing PDM..."
	@$(CONDA_EXE) run -n $(ENV_NAME) pip install pdm || \
		(echo "❌ Failed to install PDM"; exit 1)
	@echo "✅ PDM installed successfully"

# Install project dependencies
install_deps: install_pdm
	@echo "📚 Installing project dependencies with PDM..."
	@$(CONDA_EXE) run -n $(ENV_NAME) pdm install || \
		(echo "❌ Failed to install dependencies"; exit 1)
	@echo "✅ Dependencies installed successfully"

# Install development dependencies
dev: install_deps
	@echo "🛠️ Installing development dependencies..."
	@$(CONDA_EXE) run -n $(ENV_NAME) pdm install -G dev || \
		(echo "❌ Failed to install development dependencies"; exit 1)
	@echo "✅ Development dependencies installed successfully"

# Run tests
test:
	@echo "🧪 Running tests..."
	@$(CONDA_EXE) run -n $(ENV_NAME) pdm run pytest || \
		(echo "❌ Tests failed"; exit 1)

# Clean the conda environment
clean: check_conda
	@echo "🧹 Removing conda environment $(ENV_NAME)..."
	@$(CONDA_EXE) env remove -n $(ENV_NAME) -y || \
		(echo "❌ Failed to remove conda environment '$(ENV_NAME)'."; \
		 echo "   This can happen if the environment does not exist or if there are other issues with conda."; \
		 exit 1)
	@echo "✅ Conda environment '$(ENV_NAME)' has been removed."

# Build source and universal wheel distributions
build:
	@echo "📦 Building sdist and universal wheel..."
	@$(CONDA_EXE) run -n $(ENV_NAME) pdm build || \
		(echo "❌ Build failed"; exit 1)
	@echo "✅ Build complete. Distributions are in the dist/ directory."
