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
* ``numpy`` - Numerical computing
* ``pandas`` - Data manipulation and analysis
* ``requests`` - HTTP library for API calls
* ``pyyaml`` - YAML configuration file support
* ``tqdm`` - Progress bars
* ``zstandard`` - Compression support

Optional dependencies for visualization:

* ``ipywidgets`` - Interactive widgets for Jupyter
* ``ipyleaflet`` - Interactive maps
* ``folium`` - Alternative mapping library

Installing from PyPI
--------------------

The easiest way to install Φ-Down is using pip:

.. code-block:: bash

   pip install phidown

This will install the core package with all required dependencies.

Installing with Visualization Support
---------------------------------------

To use interactive features like polygon selection tools:

.. code-block:: bash

   pip install phidown[viz]

This installs the visualization dependencies (``ipywidgets``, ``folium``).

Installing from Source
----------------------

To install the latest development version:

.. code-block:: bash

   git clone https://github.com/ESA-PhiLab/phidown.git
   cd phidown
   pip install -e .

For development with all optional dependencies:

.. code-block:: bash

   git clone https://github.com/ESA-PhiLab/phidown.git
   cd phidown
   pip install -e .[viz,dev]

Using PDM (Recommended for Development)
-----------------------------------------

If you're contributing to Φ-Down, use PDM for dependency management:

.. code-block:: bash

   git clone https://github.com/ESA-PhiLab/phidown.git
   cd phidown
   pdm install

This installs all dependencies including development tools.

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
