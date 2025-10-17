Getting Started
===============

Welcome to Φ-Down! This guide will help you get up and running with downloading Copernicus satellite data.

What is Φ-Down?
---------------

Φ-Down is a Python library that provides a simple interface to search and download Earth Observation data from the Copernicus Data Space Ecosystem. It supports all major Sentinel missions and provides both programmatic access and interactive tools.

Prerequisites
-------------

Before using Φ-Down, you'll need:

1. **Python 3.9+** - Φ-Down requires Python 3.9 or later
2. **Copernicus Data Space Account** - Register at `<https://dataspace.copernicus.eu/>`_
3. **S3 Credentials** (required) - Get S3 credentials from the `S3 Key Manager <https://eodata-s3keysmanager.dataspace.copernicus.eu/panel/s3-credentials>`_

First Steps
-----------

1. **Install Φ-Down**:

   .. code-block:: bash

      pip install phidown

2. **Set up your S3 credentials**:

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

   Replace `your_access_key` and `access_key_secret` with your actual S3 credentials.

3. **Your first search**:

   .. code-block:: python

      from phidown import CopernicusDataSearcher

      # Initialize the searcher
      searcher = CopernicusDataSearcher()
      
      # Search for Sentinel-2 data over Rome
      searcher.query_by_filter(
         collection_name='SENTINEL-2',
         aoi_wkt='POLYGON((12.4 41.9, 12.5 41.9, 12.5 42.0, 12.4 42.0, 12.4 41.9))',
         start_date='2023-01-01',
         end_date='2023-01-31'
      )
      
      df = searcher.execute_query()

      # Display results
      print(f"Number of results: {len(df)}")
      # Display the first few rows of the DataFrame
      print(searcher.display_results(top_n=15))

4. **Download data**:

   .. code-block:: python

      from phidown.downloader import pull_down
      import os

      # Download the first product
      if len(df) > 0:
         product_s3_path = df.iloc[0]["S3Path"]  # or "RemotePath"
         download_dir = os.path.abspath("./data")
         pull_down(product_s3_path, output_dir=download_dir)

What's Next?
------------

* Read the :doc:`user_guide` for detailed usage instructions
* Check out the :doc:`examples` for common use cases
* Explore the :doc:`api_reference` for complete API documentation
* Review mission-specific guides:
  - :doc:`sentinel1_reference` for SAR data parameters
  - :doc:`sentinel2_reference` for optical data parameters  
  - :doc:`sentinel3_reference` for ocean/land data parameters
* Try the interactive tools for polygon selection and visualization

Common Issues
-------------

**Authentication errors**: Make sure your credentials are correct and your account is active.

**Network timeouts**: Large files may take time to download. Consider using S3 credentials for faster access.

**Import errors**: Ensure all dependencies are installed. Some features require optional dependencies like ``ipyleaflet``.

Need Help?
----------

* Check the `GitHub Issues <https://github.com/ESA-PhiLab/phidown/issues>`_ page
* Join the `PhiLab LinkedIn Group <https://www.linkedin.com/groups/8984375/>`_
* Contact the author on `LinkedIn <https://www.linkedin.com/in/roberto-del-prete-8175a7147/>`_
