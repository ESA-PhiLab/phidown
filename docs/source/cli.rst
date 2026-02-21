.. _cli:

===========================================
Command-Line Interface (CLI)
===========================================

**NEW:** Φ-Down includes a command-line interface for download, product listing, and burst coverage analysis directly from your terminal.

Overview
========

The ``phidown`` CLI provides a convenient way to work with Earth Observation products without writing Python code. It supports:

- Download by product name
- Download by S3 path
- Product listing over AOI/date filters
- Sentinel-1 burst coverage analysis over AOI/date filters

Installation
============

The CLI is included when you install phidown:

.. code-block:: bash

   pip install phidown

Prerequisites
-------------

The CLI requires ``s5cmd`` to be installed for data downloads:

**macOS (using Homebrew):**

.. code-block:: bash

   brew install peak/tap/s5cmd

**Linux/macOS (using Go):**

.. code-block:: bash

   go install github.com/peak/s5cmd/v2@latest

**Download binary directly:**

Visit https://github.com/peak/s5cmd/releases and download the appropriate binary for your system.

**Verify installation:**

.. code-block:: bash

   s5cmd version

Quick Start
===========

After installation, you can use the ``phidown`` command directly:

.. code-block:: bash

   # Download by product name
   phidown --name S1A_IW_GRDH_1SDV_20240503T031926_20240503T031942_053701_0685FB_E003 -o ./data

   # Download by S3 path
   phidown --s3path /eodata/Sentinel-1/SAR/IW_GRDH_1S/2024/05/03/... -o ./data

   # List products over area and dates
   phidown --list --collection SENTINEL-1 --product-type GRD --bbox -5 40 5 45 --start-date 2024-01-01T00:00:00 --end-date 2024-01-31T23:59:59

   # Burst coverage analysis over area and dates
   phidown --burst-coverage --bbox -5 40 5 45 --start-date 2024-08-02T00:00:00 --end-date 2024-08-15T23:59:59 --polarisation VV --format json

Command-Line Options
====================

Basic Usage
-----------

.. code-block:: text

   phidown [OPTIONS]

Required Arguments (choose one)
--------------------------------

``--name NAME``
   Product name to download (e.g., ``S1A_IW_GRDH_1SDV_...``)

   Example:
   
   .. code-block:: bash
   
      phidown --name S1A_IW_GRDH_1SDV_20240503T031926_20240503T031942_053701_0685FB_E003 -o ./data

``--s3path S3PATH``
   S3 path to download (must start with ``/eodata/``)

   Example:
   
   .. code-block:: bash
   
      phidown --s3path /eodata/Sentinel-1/SAR/IW_GRDH_1S/2024/05/03/S1A_IW_GRDH_1SDV.SAFE -o ./data

``--list``
   List products using AOI/date filters

``--burst-coverage``
   Analyze Sentinel-1 burst coverage over AOI/date range

Optional Arguments
------------------

``-o, --output-dir OUTPUT_DIR``
   Output directory for downloaded data (default: current directory)

   Example:
   
   .. code-block:: bash
   
      phidown --name PRODUCT_NAME -o /data/sentinel1

``-c, --config-file CONFIG_FILE``
   Path to s5cmd configuration file (default: ``.s5cfg``)

   Example:
   
   .. code-block:: bash
   
      phidown --name PRODUCT_NAME -o ./data -c ~/.my-s5cfg

``--reset``
   Reset configuration file and prompt for new credentials

   Example:
   
   .. code-block:: bash
   
      phidown --name PRODUCT_NAME -o ./data --reset

``--no-progress``
   Disable progress bar during download

   Example:
   
   .. code-block:: bash
   
      phidown --name PRODUCT_NAME -o ./data --no-progress

``--no-download-all``
   Download specific file instead of entire directory (for S3 path only)

   Example:
   
   .. code-block:: bash
   
      phidown --s3path /eodata/Sentinel-1/SAR/.../file.tiff -o ./data --no-download-all

``-v, --verbose``
   Enable verbose output

   Example:
   
   .. code-block:: bash
   
      phidown --name PRODUCT_NAME -o ./data -v

``--version``
   Show program's version number and exit

``-h, --help``
   Show help message and exit

Listing and Analysis Filters
----------------------------

``--collection COLLECTION``
   Collection for ``--list`` (default: ``SENTINEL-1``)

``--product-type PRODUCT_TYPE``
   Product type for ``--list`` (e.g., ``GRD``, ``SLC``, ``S2MSI1C``)

``--orbit-direction {ASCENDING,DESCENDING}``
   Orbit direction for ``--list`` and ``--burst-coverage``

``--cloud-cover CLOUD_COVER``
   Cloud cover threshold for ``--list`` (0-100)

``--aoi-wkt AOI_WKT``
   AOI as WKT POLYGON for ``--list`` or ``--burst-coverage``

``--bbox MIN_LON MIN_LAT MAX_LON MAX_LAT``
   AOI as bounding box for ``--list`` or ``--burst-coverage``

``--start-date START_DATE`` and ``--end-date END_DATE``
   ISO 8601 date filters for ``--list`` and ``--burst-coverage``

``--top TOP``
   Max number of products for ``--list`` (default: ``50``)

``--order-by ORDER_BY``
   Sorting expression for ``--list`` (default: ``ContentDate/Start desc``)

``--polarisation {VV,VH,HH,HV}``
   Polarisation for ``--burst-coverage`` (default: ``VV``)

``--relative-orbit-number RELATIVE_ORBIT_NUMBER``
   Optional relative orbit filter for ``--burst-coverage``

``--preferred-subswath PREFERRED_SUBSWATH``
   Comma-separated subswath preference order for ``--burst-coverage`` (e.g., ``IW1,IW2,IW3``)

``--format {table,json,csv}``
   Output format for ``--list`` and ``--burst-coverage`` (default: ``table``)

``--columns COLUMNS``
   Comma-separated columns to print for ``--list`` and ``--burst-coverage``

``--save SAVE``
   Save ``--list``/``--burst-coverage`` output to file instead of stdout

Listing and Burst Coverage Examples
===================================

List products in CSV:

.. code-block:: bash

   phidown --list --collection SENTINEL-2 --product-type S2MSI1C --bbox 10 45 12 46 --start-date 2024-05-01T00:00:00 --end-date 2024-05-31T23:59:59 --cloud-cover 20 --format csv --save ./outputs/s2_list.csv

List products with selected columns:

.. code-block:: bash

   phidown --list --collection SENTINEL-1 --product-type SLC --aoi-wkt "POLYGON((10 45, 12 45, 12 46, 10 46, 10 45))" --start-date 2024-08-01T00:00:00 --end-date 2024-08-31T23:59:59 --columns Name,S3Path,ContentDate,coverage

Burst coverage analysis with default orbit recommendation:

.. code-block:: bash

   phidown --burst-coverage --bbox 10 45 12 46 --start-date 2024-08-02T00:00:00 --end-date 2024-08-15T23:59:59 --polarisation VV

Burst coverage analysis with explicit orbit/subswath preferences:

.. code-block:: bash

   phidown --burst-coverage --aoi-wkt "POLYGON((10 45, 12 45, 12 46, 10 46, 10 45))" --start-date 2024-08-02T00:00:00 --end-date 2024-08-20T23:59:59 --orbit-direction DESCENDING --relative-orbit-number 22 --preferred-subswath IW1,IW2,IW3 --format json --save ./outputs/burst_coverage.json

Configuration
=============

Credentials Setup
-----------------

On first run, the CLI will prompt you to enter your Copernicus Data Space credentials. These will be stored in a configuration file (default: ``.s5cfg``).

**Manual Configuration:**

Create a ``.s5cfg`` file in your working directory:

.. code-block:: ini

   [default]
   aws_access_key_id = your_access_key
   aws_secret_access_key = your_secret_key
   aws_region = eu-central-1
   host_base = eodata.dataspace.copernicus.eu
   host_bucket = eodata.dataspace.copernicus.eu
   use_https = true
   check_ssl_certificate = true

**Getting Credentials:**

1. Log in to https://eodata-s3keysmanager.dataspace.copernicus.eu/panel/s3-credentials
2. Create new S3 credentials
3. Copy the access key and secret key

**Resetting Credentials:**

Use the ``--reset`` flag to enter new credentials:

.. code-block:: bash

   phidown --name PRODUCT_NAME -o ./data --reset

Usage Examples
==============

Download by Product Name
-------------------------

Download a Sentinel-1 product:

.. code-block:: bash

   phidown --name S1A_IW_GRDH_1SDV_20240503T031926_20240503T031942_053701_0685FB_E003 -o ~/downloads

Download a Sentinel-2 product:

.. code-block:: bash

   phidown --name S2A_MSIL2A_20240503T101031_N0510_R022_T32TQM_20240503T162538 -o ~/sentinel2_data

Download by S3 Path
-------------------

Download using the full S3 path:

.. code-block:: bash

   phidown --s3path /eodata/Sentinel-1/SAR/IW_GRDH_1S/2024/05/03/S1A_IW_GRDH_1SDV.SAFE -o ./data

Download a specific file from S3:

.. code-block:: bash

   phidown --s3path /eodata/Sentinel-1/SAR/.../measurement/file.tiff -o ./data --no-download-all

Custom Configuration
--------------------

Use a custom configuration file:

.. code-block:: bash

   phidown --name PRODUCT_NAME -o ./data -c ~/.custom-s5cfg

Download without progress bar (useful for scripts):

.. code-block:: bash

   phidown --name PRODUCT_NAME -o ./data --no-progress

Verbose output for debugging:

.. code-block:: bash

   phidown --name PRODUCT_NAME -o ./data -v

Batch Downloads
---------------

Download multiple products using a shell script:

.. code-block:: bash

   #!/bin/bash
   # download_products.sh
   
   products=(
       "S1A_IW_GRDH_1SDV_20240503T031926_20240503T031942_053701_0685FB_E003"
       "S1A_IW_GRDH_1SDV_20240504T031926_20240504T031942_053716_068612_A45F"
       "S1A_IW_GRDH_1SDV_20240505T031926_20240505T031942_053731_068629_BC21"
   )
   
   for product in "${products[@]}"; do
       echo "Downloading $product..."
       phidown --name "$product" -o ./downloads
   done

Python API
==========

You can also use the CLI functions programmatically in your Python code:

Download by Product Name
-------------------------

.. code-block:: python

   from phidown import download_by_name

   success = download_by_name(
       product_name='S1A_IW_GRDH_1SDV_20240503T031926_20240503T031942_053701_0685FB_E003',
       output_dir='./downloads',
       config_file='.s5cfg',
       show_progress=True,
       reset_config=False
   )

   if success:
       print("Download completed successfully!")
   else:
       print("Download failed!")

Download by S3 Path
-------------------

.. code-block:: python

   from phidown import download_by_s3path

   success = download_by_s3path(
       s3_path='/eodata/Sentinel-1/SAR/IW_GRDH_1S/2024/05/03/S1A_IW_GRDH_1SDV.SAFE',
       output_dir='./downloads',
       config_file='.s5cfg',
       show_progress=True,
       reset_config=False,
       download_all=True
   )

Troubleshooting
===============

s5cmd Not Found
---------------

If you see the error:

.. code-block:: text

   ERROR:phidown.cli:❌ s5cmd is not installed or not found in PATH

Install s5cmd following the instructions in the `Prerequisites`_ section.

Authentication Failed
---------------------

If authentication fails:

1. Verify your credentials are correct
2. Check if credentials have expired at https://eodata-s3keysmanager.dataspace.copernicus.eu/panel/s3-credentials
3. Use ``--reset`` to enter new credentials
4. Ensure your ``.s5cfg`` file format is correct

Product Not Found
-----------------

If a product cannot be found:

1. Verify the product name is correct (do NOT include the ``.SAFE`` extension for product names)
2. Check that the product exists in the Copernicus Data Space catalog
3. Ensure you're using the full product name exactly as it appears in the catalog

Download Progress Stalls
-------------------------

If download progress appears to stall:

1. Check your internet connection
2. Try disabling the progress bar with ``--no-progress``
3. Use ``-v`` for verbose output to see detailed transfer information
4. Verify you have sufficient disk space

Permission Denied
-----------------

If you encounter permission errors:

1. Ensure you have write permissions for the output directory
2. Check if the output directory exists and is accessible
3. Try using an absolute path for ``--output-dir``

Advanced Usage
==============

Integration with Scripts
------------------------

The CLI is designed to work well in automated scripts and workflows:

.. code-block:: bash

   #!/bin/bash
   # Automated download script
   
   # Set error handling
   set -e
   
   # Configuration
   OUTPUT_DIR="/data/sentinel1"
   CONFIG_FILE="~/.s5cfg"
   
   # Download with error handling
   if phidown --name "$PRODUCT_NAME" -o "$OUTPUT_DIR" -c "$CONFIG_FILE" --no-progress; then
       echo "✅ Download successful"
       # Process the downloaded data
       python process_data.py "$OUTPUT_DIR/$PRODUCT_NAME"
   else
       echo "❌ Download failed"
       exit 1
   fi

Exit Codes
----------

The CLI uses standard exit codes:

- ``0``: Success
- ``1``: General error (download failed, product not found, etc.)
- ``130``: Interrupted by user (Ctrl+C)

You can use these in scripts:

.. code-block:: bash

   phidown --name PRODUCT_NAME -o ./data
   if [ $? -eq 0 ]; then
       echo "Success!"
   else
       echo "Failed with exit code $?"
   fi

See Also
========

- :doc:`installation` - Installation guide
- :doc:`user_guide` - Python API usage guide
- :doc:`examples` - More usage examples
- :doc:`api_reference` - Complete API reference

.. _Prerequisites: #prerequisites
