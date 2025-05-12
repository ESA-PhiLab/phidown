#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# Define the conda environment name
ENV_NAME="phidown-env"
PYTHON_VERSION="3.9"

# Create conda environment
echo "Creating conda environment $ENV_NAME with Python $PYTHON_VERSION..."
conda create -n $ENV_NAME python=$PYTHON_VERSION -y

# Activate conda environment
echo "Activating conda environment $ENV_NAME..."
# Note: conda activate might not work directly in a script in all shells.
# Users might need to run 'conda activate phidown-env' manually after the script,
# or source this script '. install.sh' for activate to take effect in the current shell.
# Attempting to initialize conda for the current shell (bash/zsh)
if [ -n "$BASH_VERSION" ]; then
    source $(conda info --base)/etc/profile.d/conda.sh
elif [ -n "$ZSH_VERSION" ]; then
    source $(conda info --base)/etc/profile.d/conda.sh
else
    echo "Unsupported shell. Please activate the conda environment manually: conda activate $ENV_NAME"
fi
conda activate $ENV_NAME

# Install pdm
echo "Installing pdm..."
pip install pdm

# Install project dependencies using pdm
echo "Installing project dependencies with pdm..."
pdm install

echo "Installation complete. Please activate the environment if not already active: conda activate $ENV_NAME"
