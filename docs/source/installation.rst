Installation
============

Requirements
------------

Phi-Down requires:

* Python 3.9 or newer
* ``s5cmd`` on your ``PATH`` for S3 downloads
* Copernicus Data Space credentials for authenticated downloads

Install from PyPI
-----------------

Install the base package:

.. code-block:: bash

   pip install phidown

Install optional feature groups as needed:

.. code-block:: bash

   # Interactive plotting and footprint maps
   pip install "phidown[viz]"

   # AIS download and filtering support
   pip install "phidown[ais]"

   # Notebook-oriented dependencies
   pip install "phidown[jupyter_env]"

   # Development, tests, and documentation
   pip install "phidown[dev,test,docs]"

Optional Dependency Groups
--------------------------

Phi-Down exposes these optional dependency groups in ``pyproject.toml``:

* ``viz``: Folium, raster/plotting, and map visualization helpers
* ``ais``: AIS download support, including spatial filtering dependencies
* ``jupyter_env``: Jupyter widgets and notebook integrations
* ``dev``: Development tools such as ``pytest`` and ``flake8``
* ``test``: Test-only dependencies used by the local suite
* ``docs``: Sphinx and related documentation tooling

Install from Source
-------------------

Using ``pip``:

.. code-block:: bash

   git clone https://github.com/ESA-PhiLab/phidown.git
   cd phidown
   pip install -e .

With optional extras:

.. code-block:: bash

   pip install -e ".[viz,ais,dev,test,docs]"

Using PDM
---------

For local development, PDM matches the repository setup:

.. code-block:: bash

   git clone https://github.com/ESA-PhiLab/phidown.git
   cd phidown
   pdm install

To include optional groups:

.. code-block:: bash

   pdm install -G viz -G ais -G dev -G test -G docs -G jupyter_env

Install ``s5cmd``
-----------------

Phi-Down uses ``s5cmd`` for S3 transfers. Install it separately if you plan to
download data:

.. code-block:: bash

   brew install peak/tap/s5cmd

or

.. code-block:: bash

   go install github.com/peak/s5cmd/v2@latest

Then verify:

.. code-block:: bash

   s5cmd version

Configure ``.s5cfg``
--------------------

Phi-Down uses an ``.s5cfg`` file to source CDSE S3 credentials for download
operations.

Recommended template:

.. code-block:: ini

   [default]
   aws_access_key_id = your_access_key
   aws_secret_access_key = your_secret_key
   aws_region = eu-central-1
   host_base = eodata.dataspace.copernicus.eu
   host_bucket = eodata.dataspace.copernicus.eu
   use_https = true
   check_ssl_certificate = true

Guidelines:

* Keep the section name as ``[default]``.
* Store the file in the working directory as ``.s5cfg`` if you want to rely on
  Phi-Down defaults.
* If you keep credentials elsewhere, pass the path explicitly with
  ``-c/--config-file`` in the CLI or ``config_file=...`` in Python.
* Keep ``host_base`` and ``host_bucket`` aligned with the CDSE endpoint shown
  above.
* Phi-Down parses this file itself and then sets the relevant environment
  variables for ``s5cmd``.
* Avoid committing the file to git. Add ``.s5cfg`` to your local ignore rules
  if needed.
* Rotate credentials in the CDSE S3 key manager if a file is exposed or copied
  to an untrusted environment.

Example custom path usage:

.. code-block:: bash

   phidown --name PRODUCT_NAME -o ./data -c ~/.config/phidown/cdse.s5cfg

.. code-block:: python

   from pathlib import Path
   from phidown import CopernicusDataSearcher

   searcher = CopernicusDataSearcher()
   searcher.download_product(
       eo_product_name="PRODUCT_NAME",
       output_dir="./data",
       config_file=str(Path.home() / ".config/phidown/cdse.s5cfg"),
   )

Verification
------------

Check that the package imports and reports the expected version:

.. code-block:: python

   import phidown
   print(phidown.__version__)

   from phidown import CopernicusDataSearcher
   searcher = CopernicusDataSearcher()
   print(type(searcher).__name__)

Troubleshooting
---------------

``s5cmd: command not found``
   Install ``s5cmd`` and make sure it is available on your ``PATH``.

Missing optional dependencies
   Install the relevant extra, such as ``phidown[viz]`` or ``phidown[ais]``.

Import errors in notebooks
   Install ``phidown[jupyter_env]`` for widget and notebook integrations.

Authentication failures
   Recreate your ``.s5cfg`` file with fresh Copernicus Data Space S3
   credentials before retrying downloads.
