User Guide
==========

This guide covers the main Phi-Down workflows: searching, downloading,
command-line usage, interactive polygon selection, plotting, and AIS data
access.

Search Workflow
---------------

The core Python workflow uses ``CopernicusDataSearcher``:

.. code-block:: python

   from phidown import CopernicusDataSearcher

   searcher = CopernicusDataSearcher()
   searcher.query_by_filter(
       collection_name="SENTINEL-1",
       product_type="GRD",
       aoi_wkt="POLYGON((12.4 41.9, 12.5 41.9, 12.5 42.0, 12.4 42.0, 12.4 41.9))",
       start_date="2024-01-01T00:00:00",
       end_date="2024-01-31T23:59:59",
       orbit_direction="DESCENDING",
       top=25,
   )
   results = searcher.execute_query()

   print(results.columns.tolist())
   print(searcher.display_results(top_n=5))

Common Filters
--------------

The most frequently used ``query_by_filter()`` parameters are:

* ``collection_name``: Mission or collection such as ``SENTINEL-1`` or ``SENTINEL-2``
* ``product_type``: Product identifier such as ``GRD``, ``SLC``, ``S2MSI1C``, or ``OL_2_WFR___``
* ``aoi_wkt``: Area of interest as WKT in EPSG:4326. Supported types are ``POINT``,
  ``MULTIPOINT``, ``LINESTRING``, ``MULTILINESTRING``, ``POLYGON``, and ``MULTIPOLYGON``
* ``start_date`` and ``end_date``: ISO 8601 time filters
* ``orbit_direction``: ``ASCENDING`` or ``DESCENDING`` where applicable
* ``cloud_cover_threshold``: Cloud filtering for optical collections
* ``attributes``: Additional mission-specific attribute filters
* ``top`` and ``order_by``: Result count and ordering controls
* ``skip``: Manual page offset for frontend-style pagination
* ``count``: Eagerly retrieves all pages when the result count exceeds ``top``

Manual Pagination With ``skip``
-------------------------------

Use ``skip`` when you want one page at a time instead of automatic full-result
pagination.

.. code-block:: python

   from phidown import CopernicusDataSearcher

   filters = dict(
       collection_name="SENTINEL-1",
       product_type="GRD",
       start_date="2024-01-01T00:00:00",
       end_date="2024-01-31T23:59:59",
       top=20,
   )

   searcher = CopernicusDataSearcher()
   searcher.query_by_filter(**filters, skip=0)
   first_page = searcher.execute_query()

   searcher.query_by_filter(**filters, skip=20)
   second_page = searcher.execute_query()

Use this pattern for "load more" buttons or infinite scroll UIs. ``count=True``
still performs eager multi-page retrieval and cannot be combined with
``skip``.

Search by Product Name
----------------------

If you already know the product identifier, use ``query_by_name()``:

.. code-block:: python

   from phidown import CopernicusDataSearcher

   searcher = CopernicusDataSearcher()
   result = searcher.query_by_name(
       "S1A_IW_GRDH_1SDV_20240503T031926_20240503T031942_053701_0685FB_E003"
   )

   print(result[["Name", "S3Path"]].head(1))

``.s5cfg`` Configuration
------------------------

Download workflows use an ``.s5cfg`` credentials file. Phi-Down expects the
credentials in the ``[default]`` section and uses that file to populate the
environment for ``s5cmd``.

Example:

.. code-block:: ini

   [default]
   aws_access_key_id = your_access_key
   aws_secret_access_key = your_secret_key
   aws_region = eu-central-1
   host_base = eodata.dataspace.copernicus.eu
   host_bucket = eodata.dataspace.copernicus.eu
   use_https = true
   check_ssl_certificate = true

Practical rules:

* Default lookup is ``./.s5cfg`` unless you pass another file path.
* Use ``-c/--config-file`` in the CLI or ``config_file=...`` in Python when
  the file lives elsewhere.
* Keep the endpoint values exactly aligned with the CDSE S3 service unless you
  know you need a different endpoint.
* Treat the file as a secret and avoid checking it into git.
* If you use ``--reset`` in the CLI, Phi-Down can recreate the file
  interactively for download commands.

Downloads
---------

Download a single product by name:

.. code-block:: python

   from phidown import CopernicusDataSearcher

   searcher = CopernicusDataSearcher()
   searcher.download_product(
       eo_product_name="S1A_IW_GRDH_1SDV_20240503T031926_20240503T031942_053701_0685FB_E003",
       output_dir="./data",
       config_file=".s5cfg",
   )

Download multiple products from a DataFrame:

.. code-block:: python

   from phidown import CopernicusDataSearcher

   searcher = CopernicusDataSearcher()
   searcher.query_by_filter(
       collection_name="SENTINEL-2",
       product_type="S2MSI2A",
       start_date="2024-05-01T00:00:00",
       end_date="2024-05-05T23:59:59",
       aoi_wkt="POLYGON((12.4 41.9, 12.5 41.9, 12.5 42.0, 12.4 42.0, 12.4 41.9))",
       top=10,
   )
   results = searcher.execute_query()

   summary = searcher.download_products(
       df=results.head(3),
       output_dir="./data",
       config_file=".s5cfg",
        mode="safe",
       retry_count=3,
   )
   print(summary)

Command Line Usage
------------------

The CLI supports downloads, product listing, and burst coverage analysis.

.. code-block:: bash

   # Download by product name
   phidown --name S1A_IW_GRDH_1SDV_20240503T031926_20240503T031942_053701_0685FB_E003 -o ./data

   # Download by direct S3 path
   phidown --s3path /eodata/Sentinel-1/SAR/IW_GRDH_1S/2024/05/03/... -o ./data

   # List products
   phidown list --collection SENTINEL-2 --product-type S2MSI2A --bbox 10 45 12 46 --start-date 2024-05-01T00:00:00 --end-date 2024-05-31T23:59:59 --format csv

   # Burst coverage analysis
   phidown --burst-coverage --bbox 10 45 12 46 --start-date 2024-08-02T00:00:00 --end-date 2024-08-20T23:59:59 --polarisation VV --format json

Use ``--mode safe`` on download commands to prioritize resumable native
downloads. Use ``--mode fast`` to prefer the ``s5cmd`` transfer path.

If your credentials file is not in the current working directory, pass it
explicitly:

.. code-block:: bash

   phidown --name PRODUCT_NAME -o ./data -c ~/.config/phidown/cdse.s5cfg

Interactive Polygon Tools
-------------------------

Interactive polygon selection requires the optional notebook dependencies.

.. code-block:: python

   from phidown import create_polygon_tool, search_with_polygon

   tool = create_polygon_tool(center=(45.0, 9.0), zoom=8, basemap_type="satellite")
   tool.display()

   # After drawing at least one polygon in the notebook:
   results = search_with_polygon(
       tool,
       collection_name="SENTINEL-2",
       product_type="S2MSI1C",
       start_date="2024-06-01T00:00:00",
       end_date="2024-06-30T23:59:59",
       top=10,
   )

Plotting Footprints
-------------------

Use ``plot_product_footprints()`` with a results DataFrame:

.. code-block:: python

   from phidown import CopernicusDataSearcher, plot_product_footprints

   aoi_wkt = "POLYGON((12.4 41.9, 12.5 41.9, 12.5 42.0, 12.4 42.0, 12.4 41.9))"

   searcher = CopernicusDataSearcher()
   searcher.query_by_filter(
       collection_name="SENTINEL-1",
       product_type="SLC",
       aoi_wkt=aoi_wkt,
       start_date="2024-08-01T00:00:00",
       end_date="2024-08-05T23:59:59",
       top=20,
   )
   results = searcher.execute_query()

   footprint_map = plot_product_footprints(results, aoi_wkt=aoi_wkt, top_n=10)
   footprint_map.save("footprints.html")

``plot_kml_coordinates()`` is available when you want to render a KML overlay
instead of a search result DataFrame.

AIS Data
--------

AIS support is optional and documented in more detail in :doc:`ais_guide`.

.. code-block:: python

   from phidown import download_ais_data

   df = download_ais_data(
       start_date="2025-08-25",
       end_date="2025-08-26",
       start_time="10:00:00",
       end_time="12:00:00",
       aoi_wkt="POLYGON((4.0 51.0,5.0 51.0,5.0 52.0,4.0 52.0,4.0 51.0))",
   )

Tips
----

* Prefer narrow date windows and explicit AOIs to keep result sets manageable.
* Use ``query_by_name()`` when you already know the exact product identifier.
* Install the matching optional extras before using notebooks, plotting, or AIS helpers.
* Use ``mode="safe"`` or CLI ``--mode safe`` for longer downloads.
* Keep your ``.s5cfg`` in a predictable location and pass it explicitly in
  automation instead of relying on the current working directory.
