#!/bin/bash
"""
Test script to simulate the CI build process locally.
This helps debug CI issues by running the same commands locally.
"""

set -e  # Exit on any error

echo "=== Testing CI Build Process ==="
echo "Current directory: $(pwd)"

echo "--- Step 1: Check repository structure ---"
echo "Contents of current directory:"
ls -la

echo "--- Step 2: Check docs directory ---"
echo "Contents of docs directory:"
ls -la docs/

echo "--- Step 3: Check docs/source directory ---"
echo "Contents of docs/source directory:"
ls -la docs/source/

echo "--- Step 4: Check Python environment ---"
python --version
pip --version

echo "--- Step 5: Install dependencies ---"
pip install -r docs/requirements.txt
pip install -e .

echo "--- Step 6: Build documentation ---"
# Create build directory if it doesn't exist
mkdir -p docs/build/html

# Build from the repository root using full paths
sphinx-build -b html docs/source docs/build/html -v

echo "--- Step 7: Check build output ---"
echo "Contents of docs/build/html:"
ls -la docs/build/html/

echo "--- Step 8: Create .nojekyll file ---"
touch docs/build/html/.nojekyll

echo "=== CI Build Test Complete ==="
echo "Documentation built successfully!"
