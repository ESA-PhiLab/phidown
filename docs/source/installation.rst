Installation
============

Requirements
------------

Φ-Down requires Python 3.9 or later. It has been tested on:

* Python 3.9, 3.10, 3.11, 3.12
* macOS, Linux, Windows

Dependencies
------------

Core dependencies (automatically installed):

* ``s5cmd`` - High-performance S3 client for data downloads
* ``pandas`` - Data manipulation and analysis
* ``ipyleaflet`` - Interactive maps for Jupyter notebooks
* ``huggingface-hub`` - Access to Hugging Face model hub

Optional dependency groups:

**ais** - AIS (vessel tracking) support:

* ``shapely`` - Geometric operations for spatial data

**viz** - Visualization tools:

* ``ipywidgets`` - Interactive widgets for Jupyter
* ``folium`` - Web-based interactive maps

**dev** - Development tools:

* ``pytest`` - Testing framework
* ``pytest-mock`` - Mocking library for tests
* ``flake8`` - Code style checker

**docs** - Documentation tools:

* ``sphinx`` - Documentation generator
* ``sphinx-rtd-theme`` - Read the Docs theme for Sphinx
* ``sphinx-autodoc-typehints`` - Type hints support in documentation
* ``myst-parser`` - Markdown parser for Sphinx
* ``sphinx-copybutton`` - Copy button for code blocks
* ``sphinx-autoapi`` - Automatic API documentation generation

Installing from PyPI
--------------------

The easiest way to install Φ-Down is using pip:

.. code-block:: bash

   pip install phidown

This will install the core package with all required dependencies.

Installing with Optional Features
----------------------------------

Φ-Down comes with several optional dependency groups that enable additional functionality:

**Visualization Tools**

To use interactive features like polygon selection tools and maps:

.. code-block:: bash

   pip install phidown[viz]

This installs visualization dependencies (``ipywidgets``, ``folium``).

**AIS (Automatic Identification System) Support**

For vessel tracking and maritime monitoring features:

.. code-block:: bash

   pip install phidown[ais]

This installs geometry processing dependencies (``shapely``).

**Development Tools**

For contributing to the project or running tests:

.. code-block:: bash

   pip install phidown[dev]

This installs testing and code quality tools (``pytest``, ``pytest-mock``, ``flake8``).

**Documentation Tools**

For building and contributing to documentation:

.. code-block:: bash

   pip install phidown[docs]

This installs documentation dependencies (``sphinx``, ``sphinx-rtd-theme``, etc.).

**All Optional Features**

To install everything at once:

.. code-block:: bash

   pip install phidown[ais,viz,dev,docs]

.. note::
   For most users, we recommend installing with visualization support for the best experience:
   
   .. code-block:: bash
   
      pip install phidown[viz]

Installing from Source
----------------------

To install the latest development version:

.. code-block:: bash

   git clone https://github.com/ESA-PhiLab/phidown.git
   cd phidown
   pip install -e .

For development with specific optional dependencies:

.. code-block:: bash

   git clone https://github.com/ESA-PhiLab/phidown.git
   cd phidown
   
   # Install with visualization support
   pip install -e .[viz]
   
   # Install with all optional features
   pip install -e .[ais,viz,dev,docs]

Using PDM (Recommended for Development)
-----------------------------------------

If you're contributing to Φ-Down, use PDM for dependency management:

.. code-block:: bash

   git clone https://github.com/ESA-PhiLab/phidown.git
   cd phidown
   pdm install

This installs all core dependencies. For optional dependency groups:

.. code-block:: bash

   # Install with visualization support
   pdm install --group viz

   # Install with AIS support
   pdm install --group ais

   # Install with development tools
   pdm install --group dev

   # Install with documentation tools
   pdm install --group docs

   # Install all optional groups
   pdm install --group viz --group ais --group dev --group docs

Conda Installation
------------------

Currently, Φ-Down is not available on conda-forge, but you can install it in a conda environment:

.. code-block:: bash

   conda create -n phidown python=3.12
   conda activate phidown
   pip install phidown

Verification
------------

To verify your installation:

.. code-block:: python

   import phidown
   print(phidown.__version__)

   # Test basic functionality
   from phidown import CopernicusDataSearcher
   searcher = CopernicusDataSearcher()
   print("✓ Installation successful!")

Docker Installation
--------------------

A Docker image is available for containerized usage:

.. code-block:: bash

   docker pull ghcr.io/esa-philab/phidown:latest

Or build from source:

.. code-block:: bash

   git clone https://github.com/ESA-PhiLab/phidown.git
   cd phidown
   docker build -t phidown .

Troubleshooting
---------------

**ImportError for optional dependencies**:

If you see errors about missing ``ipyleaflet`` or ``ipywidgets``, install visualization dependencies:

.. code-block:: bash

   pip install phidown[viz]

**SSL Certificate errors**:

On some systems, you may encounter SSL issues. Try:

.. code-block:: bash

   pip install --trusted-host pypi.org --trusted-host pypi.python.org phidown

**Permission errors on Windows**:

Run your command prompt as administrator or use:

.. code-block:: bash

   pip install --user phidown

**Dependency conflicts**:

If you have conflicts with existing packages, consider using a virtual environment:

.. code-block:: bash

   python -m venv phidown_env
   source phidown_env/bin/activate  # On Windows: phidown_env\Scripts\activate
   pip install phidown

Upgrading
---------

To upgrade to the latest version:

.. code-block:: bash

   pip install --upgrade phidown

To upgrade with visualization dependencies:

.. code-block:: bash

   pip install --upgrade phidown[viz]

Uninstalling
------------

To remove Φ-Down:

.. code-block:: bash

   pip uninstall phidown
