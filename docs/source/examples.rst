Examples
========

This page collects short, current examples that match the package's public API.

Example 1: Sentinel-2 Search
----------------------------

.. code-block:: python

   from phidown import CopernicusDataSearcher

   searcher = CopernicusDataSearcher()
   searcher.query_by_filter(
       collection_name="SENTINEL-2",
       product_type="S2MSI2A",
       aoi_wkt="POLYGON((12.4 41.9, 12.5 41.9, 12.5 42.0, 12.4 42.0, 12.4 41.9))",
       start_date="2024-05-01T00:00:00",
       end_date="2024-05-31T23:59:59",
       cloud_cover_threshold=20,
       top=20,
   )
   results = searcher.execute_query()

   print(f"Found {len(results)} products")
   print(searcher.display_results(top_n=5))

Example 2: Query by Product Name
--------------------------------

.. code-block:: python

   from phidown import CopernicusDataSearcher

   searcher = CopernicusDataSearcher()
   result = searcher.query_by_name(
       "S1A_IW_GRDH_1SDV_20240503T031926_20240503T031942_053701_0685FB_E003"
   )

   print(result[["Name", "S3Path", "ContentLength"]].head(1))

Example 3: Batch Download
-------------------------

.. code-block:: python

   from phidown import CopernicusDataSearcher

   searcher = CopernicusDataSearcher()
   searcher.query_by_filter(
       collection_name="SENTINEL-1",
       product_type="GRD",
       aoi_wkt="POLYGON((12.4 41.9, 12.5 41.9, 12.5 42.0, 12.4 42.0, 12.4 41.9))",
       start_date="2024-01-01T00:00:00",
       end_date="2024-01-07T23:59:59",
       top=5,
   )
   results = searcher.execute_query()

   summary = searcher.download_products(
       df=results,
       output_dir="./downloads",
       config_file=".s5cfg",
       retry_count=3,
       mode="safe",
   )
   print(summary)

Example 4: CLI Listing
----------------------

.. code-block:: bash

   phidown list \
     --collection SENTINEL-2 \
     --product-type S2MSI2A \
     --bbox 10 45 12 46 \
     --start-date 2024-05-01T00:00:00 \
     --end-date 2024-05-31T23:59:59 \
     --columns Name,S3Path,ContentDate \
     --format table

Example 5: Burst Coverage Analysis
----------------------------------

.. code-block:: bash

   phidown --burst-coverage \
     --bbox 10 45 12 46 \
     --start-date 2024-08-02T00:00:00 \
     --end-date 2024-08-20T23:59:59 \
     --polarisation VV \
     --preferred-subswath IW1,IW2,IW3 \
     --format json

Example 6: Interactive Polygon Search
-------------------------------------

.. code-block:: python

   from phidown import create_polygon_tool, search_with_polygon

   tool = create_polygon_tool(center=(45.0, 9.0), zoom=8, basemap_type="satellite")
   tool.display()

   # After drawing a polygon in the notebook UI:
   results = search_with_polygon(
       tool,
       collection_name="SENTINEL-2",
       product_type="S2MSI1C",
       start_date="2024-06-01T00:00:00",
       end_date="2024-06-30T23:59:59",
   )

Example 7: Plot Product Footprints
----------------------------------

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

Example 8: AIS Filtering
------------------------

.. code-block:: python

   from phidown import download_ais_data

   df = download_ais_data(
       start_date="2025-08-25",
       end_date="2025-08-26",
       start_time="09:00:00",
       end_time="15:00:00",
       aoi_wkt="POLYGON((4.0 51.0,5.0 51.0,5.0 52.0,4.0 52.0,4.0 51.0))",
   )

   print(df.head())

Example 9: Manual Pagination With ``skip``
------------------------------------------

.. code-block:: python

   from phidown import CopernicusDataSearcher

   filters = dict(
       collection_name="SENTINEL-2",
       product_type="S2MSI2A",
       start_date="2024-05-01T00:00:00",
       end_date="2024-05-31T23:59:59",
       top=10,
   )

   searcher = CopernicusDataSearcher()
   searcher.query_by_filter(**filters, skip=0)
   first_page = searcher.execute_query()

   searcher.query_by_filter(**filters, skip=10)
   second_page = searcher.execute_query()

   print(len(first_page), len(second_page))

.. note::

   ``count=True`` still retrieves every page eagerly and cannot be combined
   with ``skip``.
