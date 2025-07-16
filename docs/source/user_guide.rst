User Guide
==========

This guide provides detailed instructions for using Φ-Down to search and download Copernicus satellite data.

Setting Up S3 Credentials
--------------------------

Before using Φ-Down, you need to set up your S3 credentials for accessing the Copernicus Data Space Ecosystem. S3 credentials are required for downloading data.

Configuration File Method
^^^^^^^^^^^^^^^^^^^^^^^^^^

Create a `.s5cfg` file in your working directory:

.. code-block:: yaml

   [default]
   aws_access_key_id = your_access_key
   aws_secret_access_key = access_key_secret
   aws_region = eu-central-1
   host_base = eodata.dataspace.copernicus.eu
   host_bucket = eodata.dataspace.copernicus.eu
   use_https = true
   check_ssl_certificate = true

Replace `your_access_key` and `access_key_secret` with your actual S3 credentials obtained from the `S3 Key Manager <https://eodata-s3keysmanager.dataspace.copernicus.eu/panel/s3-credentials>`_.

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
* **Product Types**: 'S2MSI1C', 'S2MSI2A'
* **Use Cases**: Land cover mapping, agriculture monitoring, environmental analysis

.. code-block:: python

   results = searcher.search(
       collection_name='SENTINEL-2',
       product_type='S2MSI2A',
       cloud_cover_threshold=10,
       start_date='2023-01-01',
       end_date='2023-01-31'
   )

For detailed Sentinel-2 search parameters and examples, see the :doc:`sentinel2_reference` guide.

Sentinel-3 (Ocean/Land)
^^^^^^^^^^^^^^^^^^^^^^^

* **Collection**: 'SENTINEL-3'
* **Product Types**: 'OL_1_EFR___', 'OL_2_LFR___', 'SL_1_RBT___', 'SL_2_LST___'
* **Use Cases**: Ocean color, land surface temperature, topography

.. code-block:: python

   results = searcher.search(
       collection_name='SENTINEL-3',
       product_type='OL_2_LFR___',
       start_date='2023-01-01',
       end_date='2023-01-31',
       attributes={'instrument': 'OLCI'}
   )

For detailed Sentinel-3 search parameters and examples, see the :doc:`sentinel3_reference` guide.

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

   from phidown.s5cmd_utils import download as pull_down

   # Download a single product using S3 path
   s3_path = '/eodata/Sentinel-1/SAR/IW_RAW__0S/2024/05/03/S1A_IW_RAW__0SDV_20240503T031926_20240503T031942_053701_0685FB_E003.SAFE'
   pull_down(
       s3_path=s3_path,
       output_dir='./data',
       config_file='.s5cfg',
       endpoint_url='https://eodata.dataspace.copernicus.eu',
       download_all=True,
       reset=False
   )

Batch Download
^^^^^^^^^^^^^^

.. code-block:: python

   # Download multiple products
   for idx, row in results.iterrows():
       s3_path = row['S3Path']  # Assuming S3Path is available in results
       print(f"Downloading {row['Name']}")
       pull_down(
           s3_path=s3_path,
           output_dir='./data',
           config_file='.s5cfg'
       )

Download with S3 Configuration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The download function uses S3 credentials by default. Make sure your `.s5cfg` file is properly configured:

.. code-block:: python

   # The .s5cfg file should contain:
   # [default]
   # aws_access_key_id = your_access_key
   # aws_secret_access_key = access_key_secret
   # aws_region = eu-central-1
   # host_base = eodata.dataspace.copernicus.eu
   # host_bucket = eodata.dataspace.copernicus.eu
   # use_https = true
   # check_ssl_certificate = true
   
   # Reset configuration and prompt for new credentials
   pull_down(
       s3_path=s3_path,
       output_dir='./data',
       reset=True
   )

Command Line Usage
------------------

Φ-Down also provides a command-line interface for downloading data:

.. code-block:: bash

   # Basic usage
   python -m phidown.downloader /eodata/Sentinel-1/SAR/IW_RAW__0S/2024/05/03/S1A_IW_RAW__0SDV_20240503T031926_20240503T031942_053701_0685FB_E003.SAFE

   # Specify output directory
   python -m phidown.downloader /eodata/Sentinel-1/... -o /path/to/output

   # Use custom config file
   python -m phidown.downloader /eodata/Sentinel-1/... -c /path/to/config.s5cfg

   # Download single file instead of entire directory
   python -m phidown.downloader /eodata/Sentinel-1/... --no-download-all

   # Reset credentials
   python -m phidown.downloader /eodata/Sentinel-1/... --reset

Available CLI options:

* ``s3_path``: S3 path to the Sentinel data (must start with /eodata/)
* ``-o, --output-dir``: Local output directory (default: current directory)
* ``-c, --config-file``: Path to s5cmd configuration file (default: .s5cfg)
* ``-e, --endpoint-url``: Copernicus Data Space endpoint URL
* ``--no-download-all``: Download only specific file instead of entire directory
* ``--reset``: Reset configuration file and prompt for new credentials

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

   from phidown import CopernicusDataSearcher
   from phidown.s5cmd_utils import download as pull_down

   try:
       searcher = CopernicusDataSearcher()
       results = searcher.search(
           collection_name='SENTINEL-2',
           aoi_wkt=wkt,
           start_date='2023-01-01',
           end_date='2023-01-31'
       )
       
       if len(results) > 0:
           # Assuming results contain S3Path column
           s3_path = results.iloc[0]['S3Path']
           pull_down(
               s3_path=s3_path,
               output_dir='./data',
               config_file='.s5cfg'
           )
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
   from phidown.s5cmd_utils import download as pull_down
   import time
   
   batch_size = 10
   for i in range(0, len(results), batch_size):
       batch = results.iloc[i:i+batch_size]
       for idx, row in batch.iterrows():
           s3_path = row['S3Path']  # Assuming S3Path is available in results
           pull_down(
               s3_path=s3_path,
               output_dir='./data',
               config_file='.s5cfg'
           )
       time.sleep(1)  # Be respectful to the API
