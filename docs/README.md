# Φ-Down Documentation

This directory contains the Sphinx documentation for Φ-Down.

## Building Documentation Locally

1. Install documentation dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Build the documentation:
   ```bash
   make html
   ```

3. View the documentation:
   ```bash
   open build/html/index.html
   ```

## Documentation Structure

- `source/` - Documentation source files
  - `index.rst` - Main documentation page
  - `getting_started.rst` - Getting started guide
  - `installation.rst` - Installation instructions
  - `user_guide.rst` - Comprehensive user guide
  - `api_reference.rst` - API reference
  - `examples.rst` - Code examples
  - `contributing.rst` - Contributing guidelines
  - `changelog.rst` - Version history
  - `conf.py` - Sphinx configuration
  - `_static/` - Static files (CSS, images)
  - `_templates/` - Custom templates

- `build/` - Generated documentation (HTML)

## GitHub Pages Deployment

The documentation is automatically deployed to GitHub Pages when changes are pushed to the main branch. The deployment is handled by the GitHub Actions workflow in `.github/workflows/docs.yml`.

## Theme and Styling

The documentation uses the Read the Docs theme with custom styling for PhiLab branding. Custom CSS is located in `source/_static/custom.css`.

## API Documentation

API documentation is automatically generated using Sphinx AutoAPI from the Python source code docstrings. The configuration is in `conf.py`.

## Contributing to Documentation

1. Edit the relevant `.rst` files in `source/`
2. Build locally to test changes
3. Submit a pull request

For more information about reStructuredText syntax, see the [Sphinx documentation](https://www.sphinx-doc.org/en/master/usage/restructuredtext/index.html).
