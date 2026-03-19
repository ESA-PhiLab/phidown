Getting Started
===============

Phi-Down provides a Python API and CLI for searching Copernicus Data Space
products and downloading them through S3.

Prerequisites
-------------

Before you begin, make sure you have:

1. Python 3.9 or newer
2. A Copernicus Data Space account: `<https://dataspace.copernicus.eu/>`_
3. S3 credentials from the `S3 Key Manager <https://eodata-s3keysmanager.dataspace.copernicus.eu/panel/s3-credentials>`_
4. ``s5cmd`` installed if you plan to download products

Install Phi-Down
----------------

.. code-block:: bash

   pip install phidown

Configure S3 Credentials
------------------------

Phi-Down reads CDSE S3 credentials from an ``.s5cfg`` file. By default it
looks for ``.s5cfg`` in your current working directory, but you can also pass a
custom path with the CLI ``-c/--config-file`` option or the Python
``config_file=...`` argument.

Create a minimal ``.s5cfg`` file:

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

* Keep the section name as ``[default]``. Phi-Down currently reads credentials
  from that section.
* ``aws_access_key_id`` and ``aws_secret_access_key`` are the critical values.
  The rest should normally stay as shown above for CDSE.
* ``host_base`` and ``host_bucket`` should both remain
  ``eodata.dataspace.copernicus.eu``.
* ``aws_region`` should remain ``eu-central-1`` unless CDSE changes its S3
  endpoint requirements.
* Values may be quoted or unquoted; Phi-Down strips wrapping quotes when
  loading the file.
* Phi-Down reads this file and forwards the values to ``s5cmd`` at runtime.
  Treat it as the Phi-Down download credential file, not as a generic
  replacement for every standalone ``s5cmd`` workflow.
* Do not commit ``.s5cfg`` to version control. On shared systems, restrict file
  permissions if possible, for example with ``chmod 600 .s5cfg``.

If you prefer to store the file outside the project directory, for example at
``~/.config/phidown/cdse.s5cfg``, point Phi-Down at it explicitly:

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

First Search
------------

The standard search flow is:

1. Create ``CopernicusDataSearcher``
2. Configure filters with ``query_by_filter()``
3. Execute the request with ``execute_query()``

.. code-block:: python

   from phidown import CopernicusDataSearcher

   searcher = CopernicusDataSearcher()
   searcher.query_by_filter(
       collection_name="SENTINEL-2",
       product_type="S2MSI2A",
       aoi_wkt="POLYGON((12.4 41.9, 12.5 41.9, 12.5 42.0, 12.4 42.0, 12.4 41.9))",
       start_date="2024-05-01T00:00:00",
       end_date="2024-05-31T23:59:59",
       top=20,
   )
   results = searcher.execute_query()

   print(f"Found {len(results)} products")
   print(searcher.display_results(top_n=5))

First Download
--------------

Download a product by name from Python:

.. code-block:: python

   from phidown import CopernicusDataSearcher

   searcher = CopernicusDataSearcher()
   searcher.download_product(
       eo_product_name="S1A_IW_GRDH_1SDV_20240503T031926_20240503T031942_053701_0685FB_E003",
       output_dir="./data",
       config_file=".s5cfg",
       mode="fast",  # default: fast (s5cmd), or safe (resumable)
   )

For unstable connections, use safe mode with automatic retries:

.. code-block:: python

   searcher.download_product(
       eo_product_name="S1A_IW_GRDH_1SDV_20240503T031926_20240503T031942_053701_0685FB_E003",
       output_dir="./data",
       mode="safe",
       retry_count=5,
   )

Or use the CLI directly:

.. code-block:: bash

   # Fast mode (default)
   phidown --name S1A_IW_GRDH_1SDV_20240503T031926_20240503T031942_053701_0685FB_E003 -o ./data

   # Safe mode with retries
   phidown --name S1A_IW_GRDH_1SDV_20240503T031926_20240503T031942_053701_0685FB_E003 -o ./data --mode safe --retry-count 5

Useful Next Steps
-----------------

* Read :doc:`user_guide` for the main workflows
* Read :doc:`cli` for terminal usage
* Read :doc:`examples` for end-to-end snippets
* Read :doc:`sentinel1_burst_mode` and :doc:`burst_mode` for burst workflows

Common Issues
-------------

Authentication errors
   Regenerate your S3 credentials, update ``.s5cfg``, and make sure you are
   using the intended file path if you keep credentials outside the working
   directory.

Empty search results
   Tight filters, unavailable dates, or invalid AOI geometries are the most
   common causes.

Download failures
   Confirm that ``s5cmd`` is installed and the product path begins with
   ``/eodata/`` when using direct S3 downloads.
