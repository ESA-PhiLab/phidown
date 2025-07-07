#!/bin/bash

# Documentation Verification Script
# This script verifies that the documentation builds correctly

echo "🔍 Verifying Sphinx Documentation Setup"
echo "======================================="

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    echo "❌ Error: Must be run from project root directory"
    exit 1
fi

# Check if docs directory exists
if [ ! -d "docs" ]; then
    echo "❌ Error: docs directory not found"
    exit 1
fi

# Check if docs/source exists
if [ ! -d "docs/source" ]; then
    echo "❌ Error: docs/source directory not found"
    exit 1
fi

# Check if conf.py exists
if [ ! -f "docs/source/conf.py" ]; then
    echo "❌ Error: docs/source/conf.py not found"
    exit 1
fi

echo "✅ Documentation structure verified"

# Check if requirements.txt exists
if [ ! -f "docs/requirements.txt" ]; then
    echo "❌ Error: docs/requirements.txt not found"
    exit 1
fi

echo "✅ Documentation requirements file found"

# Build documentation
echo "🔨 Building documentation..."
sphinx-build -b html docs/source docs/build/html -q

if [ $? -eq 0 ]; then
    echo "✅ Documentation built successfully"
else
    echo "❌ Documentation build failed"
    exit 1
fi

# Check if index.html was created
if [ -f "docs/build/html/index.html" ]; then
    echo "✅ Index page created"
else
    echo "❌ Index page not found"
    exit 1
fi

# Check if API documentation was generated
if [ -d "docs/build/html/api" ]; then
    echo "✅ API documentation generated"
else
    echo "❌ API documentation not generated"
    exit 1
fi

# Check size of generated documentation
html_count=$(find docs/build/html -name "*.html" | wc -l)
echo "📄 Generated $html_count HTML files"

if [ $html_count -gt 5 ]; then
    echo "✅ Documentation appears complete"
else
    echo "❌ Documentation appears incomplete"
    exit 1
fi

echo ""
echo "🎉 Documentation verification complete!"
echo "📖 Documentation is ready for deployment"
echo ""
echo "To view locally:"
echo "  cd docs/build/html && python -m http.server 8000"
echo ""
echo "To deploy to GitHub Pages:"
echo "  git add . && git commit -m 'Update documentation' && git push"
