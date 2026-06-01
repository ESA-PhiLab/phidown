PhiSat-2 Reference Guide
========================

.. note::

   **New in version 0.1.27:** Phi-Down supports PhiSat-2 INSULA search and
   download workflows through both the Python API and CLI.

Overview
--------

PhiSat-2 support uses the INSULA platform for product discovery and HTTP
downloads. CDSE products still use the Copernicus Data Space S3 workflow, while
PhiSat-2 products use the ``phisat2`` provider and the ``[phisat2]`` credential
section in the shared ``.s5cfg`` file.

Supported Workflows
-------------------

* Search platform files by session ID, exact filename, filename fragment, or
  another unique text token.
* Search catalogue products with product type, AOI, and date filters through
  the common ``CopernicusDataSearcher`` API.
* Download one product by exact filename, unique token, resolved product ID, or
  normalized download URL.
* Reuse the same credential file as CDSE without overwriting the ``[default]``
  S3 section.

Credentials
-----------

Create a shared ``.s5cfg`` file with both provider sections:

.. code-block:: ini

   [default]
   aws_access_key_id = your_access_key
   aws_secret_access_key = your_secret_key
   aws_region = eu-central-1
   host_base = eodata.dataspace.copernicus.eu
   host_bucket = eodata.dataspace.copernicus.eu
   use_https = true
   check_ssl_certificate = true

   [phisat2]
   username = your_email@example.com
   password = your_password
   base_url = https://phisat2.insula.earth
   api_base = https://phisat2.insula.earth/secure/api/v2.0
   authorization_endpoint = https://identity.insula.earth/realms/phisat2/protocol/openid-connect/auth
   token_endpoint = https://identity.insula.earth/realms/phisat2/protocol/openid-connect/token
   redirect_uri = http://localhost:9207/auth
   client_id = api-client

``username`` and ``password`` are the required PhiSat-2 values. Endpoint values
normally stay at their defaults. When ``--reset`` is used with
``--provider phisat2``, Phi-Down rewrites only the ``[phisat2]`` section.

Python API
----------

Use ``PhiSat2Searcher`` directly for platform-file searches:

.. code-block:: python

   from phidown import PhiSat2Searcher

   searcher = PhiSat2Searcher(config_file=".s5cfg")
   results = searcher.query("SESSION_ID_12345", results_per_page=10)
   print(results[["Id", "Name", "DownloadUrl"]].head())

   output_path = searcher.download_by_name(
       "SESSION_ID_12345",
       output_dir="./data",
       retry_count=3,
   )

Use the common searcher when you want collection-style search filters:

.. code-block:: python

   from phidown import CopernicusDataSearcher

   searcher = CopernicusDataSearcher()
   searcher.query_by_filter(
       collection_name="PHISAT-2",
       product_type="L1",
       aoi_wkt="POLYGON((-3.90 40.30, -3.50 40.30, -3.50 40.70, -3.90 40.70, -3.90 40.30))",
       start_date="2026-05-01T00:00:00Z",
       end_date="2026-05-30T23:59:59Z",
       top=10,
       config_file=".s5cfg",
   )
   results = searcher.execute_query()

   print(results[["Id", "coverage", "Name", "ContentDate", "DownloadUrl"]].head())

CLI
---

List matching PhiSat-2 products:

.. code-block:: bash

   phidown list --provider phisat2 --filter SESSION_ID_12345

Download a PhiSat-2 product by exact filename or unique search token:

.. code-block:: bash

   phidown --provider phisat2 --name SESSION_ID_12345 -o ./data

Refresh only the PhiSat-2 credential section:

.. code-block:: bash

   phidown --provider phisat2 --name SESSION_ID_12345 -o ./data --reset

Result Columns
--------------

PhiSat-2 result frames normalize common columns where available:

.. table:: PhiSat-2 Result Columns
   :widths: 24 56

   ==================  ==================================================
   Column              Description
   ==================  ==================================================
   ``Id``              INSULA platform file or catalogue feature ID
   ``Name``            Product filename or normalized title
   ``ContentLength``   Product size in bytes when provided by INSULA
   ``ContentDate``     Product acquisition date range when provided
   ``GeoFootprint``    Product footprint as GeoJSON geometry
   ``DownloadUrl``     Normalized INSULA download URL
   ``Provider``        Always ``phisat2`` for PhiSat-2 results
   ``coverage``        AOI coverage percentage when AOI and footprint exist
   ==================  ==================================================

Limitations
-----------

* PhiSat-2 searches do not support Sentinel-1 burst mode.
* ``--s3path`` is CDSE-only; PhiSat-2 downloads use INSULA HTTP URLs.
* ``phidown list --provider phisat2`` requires ``--filter``.
* PhiSat-2 authentication requires ``InsulaWorkflowClient``.

API Objects
-----------

.. automodule:: phidown.phisat2
   :members:
   :undoc-members:
   :show-inheritance:
   :no-index:
