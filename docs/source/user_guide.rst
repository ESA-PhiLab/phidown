User Guide
==========

This guide provides detailed instructions for using Φ-Down to search and download Copernicus satellite data.

Setting Up Credentials
-----------------------

Before using Φ-Down, you need to set up your Copernicus Data Space credentials.

Method 1: Configuration File
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Create a ``secret.yml`` file in your working directory:

.. code-block:: yaml

   username: your_username
   password: your_password

Method 2: Interactive Setup
^^^^^^^^^^^^^^^^^^^^^^^^^^^

If no configuration file is found, Φ-Down will prompt you for credentials:

.. code-block:: python

   from phidown.downloader import load_credentials
   username, password = load_credentials()

Method 3: Environment Variables
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Set environment variables (useful for CI/CD):

.. code-block:: bash

   export COPERNICUS_USERNAME=your_username
   export COPERNICUS_PASSWORD=your_password

Searching for Data
------------------

The ``CopernicusDataSearcher`` class provides flexible search capabilities.

Basic Search
^^^^^^^^^^^^

.. code-block:: python

   from phidown import CopernicusDataSearcher

   searcher = CopernicusDataSearcher()
   
   # Search for Sentinel-2 data
   results = searcher.search(
       collection_name='SENTINEL-2',
       aoi_wkt='POLYGON((12.4 41.9, 12.5 41.9, 12.5 42.0, 12.4 42.0, 12.4 41.9))',
       start_date='2023-01-01',
       end_date='2023-01-31'
   )

Search Parameters
^^^^^^^^^^^^^^^^^

Available search parameters:

* ``collection_name``: Mission name (e.g., 'SENTINEL-1', 'SENTINEL-2')
* ``product_type``: Product type (e.g., 'L1C', 'L2A')
* ``aoi_wkt``: Area of interest in WKT format
* ``start_date``: Start date (YYYY-MM-DD)
* ``end_date``: End date (YYYY-MM-DD)
* ``cloud_cover_threshold``: Maximum cloud cover percentage
* ``orbit_direction``: 'ASCENDING' or 'DESCENDING'
* ``attributes``: Additional filtering attributes

Advanced Search
^^^^^^^^^^^^^^^

.. code-block:: python

   # Search with multiple filters
   results = searcher.search(
       collection_name='SENTINEL-2',
       product_type='L2A',
       aoi_wkt='POLYGON((12.4 41.9, 12.5 41.9, 12.5 42.0, 12.4 42.0, 12.4 41.9))',
       start_date='2023-01-01',
       end_date='2023-01-31',
       cloud_cover_threshold=20,
       attributes={'processingLevel': 'L2A'}
   )

Supported Missions
------------------

Φ-Down supports all major Copernicus missions:

Sentinel-1 (SAR)
^^^^^^^^^^^^^^^^

* **Collection**: 'SENTINEL-1'
* **Product Types**: 'GRD', 'SLC', 'OCN'
* **Use Cases**: Land monitoring, ocean surveillance, emergency response

.. code-block:: python

   results = searcher.search(
       collection_name='SENTINEL-1',
       product_type='GRD',
       orbit_direction='DESCENDING',
       start_date='2023-01-01',
       end_date='2023-01-31'
   )

Sentinel-2 (Optical)
^^^^^^^^^^^^^^^^^^^^

* **Collection**: 'SENTINEL-2'
* **Product Types**: 'L1C', 'L2A'
* **Use Cases**: Land cover mapping, agriculture monitoring, environmental analysis

.. code-block:: python

   results = searcher.search(
       collection_name='SENTINEL-2',
       product_type='L2A',
       cloud_cover_threshold=10,
       start_date='2023-01-01',
       end_date='2023-01-31'
   )

Sentinel-3 (Ocean/Land)
^^^^^^^^^^^^^^^^^^^^^^^

* **Collection**: 'SENTINEL-3'
* **Product Types**: 'OL_1_EFR', 'OL_2_LFR', 'SL_1_RBT', 'SL_2_LST'
* **Use Cases**: Ocean color, land surface temperature, topography

Sentinel-5P (Atmospheric)
^^^^^^^^^^^^^^^^^^^^^^^^^

* **Collection**: 'SENTINEL-5P'
* **Product Types**: 'L1B_IR_SIR', 'L1B_IR_UVN', 'L1B_RA_BD1', 'L2__AER_AI'
* **Use Cases**: Air quality monitoring, greenhouse gas measurements

Working with Results
--------------------

Search results are returned as pandas DataFrames for easy manipulation.

Displaying Results
^^^^^^^^^^^^^^^^^^

.. code-block:: python

   # Display all results
   print(results)
   
   # Display specific columns
   searcher.display_results(results, columns=['Name', 'ContentDate', 'CloudCover'])
   
   # Get result summary
   print(f"Found {len(results)} products")
   print(f"Date range: {results['ContentDate'].min()} to {results['ContentDate'].max()}")

Filtering Results
^^^^^^^^^^^^^^^^^

.. code-block:: python

   # Filter by cloud cover
   clear_results = results[results['CloudCover'] < 10]
   
   # Filter by date
   recent_results = results[results['ContentDate'] > '2023-01-15']
   
   # Sort by date
   sorted_results = results.sort_values('ContentDate')

Downloading Data
----------------

Use the ``pull_down`` function to download products:

Basic Download
^^^^^^^^^^^^^^

.. code-block:: python

   from phidown.downloader import pull_down

   # Download a single product
   product_id = results.iloc[0]['Id']
   pull_down(product_id, download_dir='./data')

Batch Download
^^^^^^^^^^^^^^

.. code-block:: python

   # Download multiple products
   for idx, row in results.iterrows():
       product_id = row['Id']
       print(f"Downloading {row['Name']}")
       pull_down(product_id, download_dir='./data')

Download with S3 (Faster)
^^^^^^^^^^^^^^^^^^^^^^^^^

For faster downloads, use S3 credentials:

.. code-block:: python

   # Set up S3 credentials in secret.yml
   # s3_access_key: your_s3_access_key
   # s3_secret_key: your_s3_secret_key
   
   pull_down(product_id, download_dir='./data', use_s3=True)

Interactive Tools
-----------------

Φ-Down provides interactive tools for Jupyter notebooks.

Polygon Selection
^^^^^^^^^^^^^^^^^

.. code-block:: python

   from phidown import create_polygon_tool

   # Create an interactive map for polygon selection
   tool = create_polygon_tool()
   tool.display()

After drawing a polygon, get the WKT:

.. code-block:: python

   wkt = tool.get_wkt()
   print(f"Selected area: {wkt}")

Search with Polygon
^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from phidown import search_with_polygon

   # Interactive search with polygon selection
   results = search_with_polygon(
       collection_name='SENTINEL-2',
       start_date='2023-01-01',
       end_date='2023-01-31'
   )

Visualization
-------------

Plot search results and coordinates:

.. code-block:: python

   from phidown import plot_kml_coordinates

   # Plot results on a map
   plot_kml_coordinates(results)

Best Practices
--------------

1. **Use specific date ranges** to avoid large result sets
2. **Filter by cloud cover** for optical missions
3. **Use S3 credentials** for faster downloads
4. **Check data availability** before downloading
5. **Organize downloads** by mission and date

Error Handling
--------------

Common errors and solutions:

**Authentication Error**:
   Check your credentials and account status.

**Network Timeout**:
   Use S3 credentials or retry with smaller batches.

**Invalid WKT**:
   Ensure your polygon coordinates are valid and in the correct order.

**Product Not Found**:
   Verify the product ID and availability.

Example workflow:

.. code-block:: python

   try:
       results = searcher.search(
           collection_name='SENTINEL-2',
           aoi_wkt=wkt,
           start_date='2023-01-01',
           end_date='2023-01-31'
       )
       
       if len(results) > 0:
           pull_down(results.iloc[0]['Id'], download_dir='./data')
       else:
           print("No products found for the given criteria")
           
   except Exception as e:
       print(f"Error: {e}")
       print("Please check your credentials and search parameters")

Configuration
-------------

Φ-Down uses a configuration file to support different missions and product types. The configuration is automatically loaded, but you can customize it if needed.

Custom Configuration
^^^^^^^^^^^^^^^^^^^^^

Create a custom ``config.json`` file:

.. code-block:: json

   {
     "SENTINEL-2": {
       "product_types": ["L1C", "L2A"],
       "description": "Multi-spectral imaging mission"
     },
     "SENTINEL-1": {
       "product_types": ["GRD", "SLC", "OCN"],
       "description": "Synthetic Aperture Radar mission"
     }
   }

Load custom configuration:

.. code-block:: python

   searcher = CopernicusDataSearcher()
   searcher.config = searcher._load_config('path/to/config.json')

Performance Tips
----------------

1. **Use specific search criteria** to reduce API calls
2. **Batch downloads** efficiently
3. **Use S3 for large files**
4. **Cache search results** to avoid repeated queries
5. **Monitor quota usage** to avoid rate limits

.. code-block:: python

   # Efficient batch processing
   batch_size = 10
   for i in range(0, len(results), batch_size):
       batch = results.iloc[i:i+batch_size]
       for idx, row in batch.iterrows():
           pull_down(row['Id'], download_dir='./data')
       time.sleep(1)  # Be respectful to the API
