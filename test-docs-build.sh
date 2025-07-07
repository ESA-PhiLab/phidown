#!/bin/bash

# Test script to simulate GitHub Actions workflow locally
echo "🚀 Testing Φ-Down Documentation Build"
echo "======================================"

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    echo "❌ Error: Please run this script from the repository root"
    exit 1
fi

# Check Python version
echo "📍 Checking Python version..."
python --version

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r docs/requirements.txt
pip install -e .

# Build documentation
echo "🔨 Building documentation..."
sphinx-build -b html docs/source docs/build/html -v

# Create .nojekyll file
echo "📝 Creating .nojekyll file..."
touch docs/build/html/.nojekyll

# Check if build was successful
if [ -f "docs/build/html/index.html" ]; then
    echo "✅ Documentation build successful!"
    echo "📂 Output directory: docs/build/html/"
    echo "🌐 Open docs/build/html/index.html in your browser to view"
else
    echo "❌ Documentation build failed!"
    exit 1
fi

echo ""
echo "🎉 All tests passed! The documentation is ready for GitHub Pages deployment."
