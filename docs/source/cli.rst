.. _cli:

========================
Command-Line Interface
========================

Phi-Down ships with a CLI for downloads, product listing, and Sentinel-1 burst
coverage analysis.

Basic Usage
-----------

.. code-block:: text

   phidown [OPTIONS]
   phidown list [OPTIONS]

Download Commands
-----------------

Download by product name:

.. code-block:: bash

   phidown --name S1A_IW_GRDH_1SDV_20240503T031926_20240503T031942_053701_0685FB_E003 -o ./data

Download by direct S3 path:

.. code-block:: bash

   phidown --s3path /eodata/Sentinel-1/SAR/IW_GRDH_1S/2024/05/03/... -o ./data

Common download options:

* ``-o, --output-dir``: Output directory for downloaded data
* ``-c, --config-file``: Path to the ``.s5cfg`` credentials file
* ``--mode {fast,safe}``: ``fast`` uses ``s5cmd`` for throughput, ``safe`` uses resumable native downloads
* ``--no-progress``: Disable the progress bar
* ``--no-download-all``: Download a single object instead of an entire directory when using ``--s3path``
* ``--reset``: Recreate credentials configuration

``.s5cfg`` notes:

* Phi-Down reads credentials from the ``[default]`` section of the specified
  file.
* If ``-c`` is omitted, Phi-Down uses ``.s5cfg`` in the current working
  directory.
* ``--reset`` is useful when a credential pair has expired and you want the
  tool to rewrite the file interactively.
* For automation, prefer an explicit config path instead of relying on the
  shell's current directory.

Download Modes
--------------

These options apply to download workflows:

* ``--mode fast``: Prefer the ``s5cmd`` transfer path for maximum throughput
* ``--mode safe``: Prefer the resumable native transfer path for interruption recovery
* ``--retry-count``: Command-level retry count
* ``--state-file``: Custom JSON state file path (default: ``.phidown/download_state.json`` in output directory)
* ``--s5cmd-retry-count``: Internal retry count passed to ``s5cmd``
* ``--max-workers``: Worker count passed to ``s5cmd``
* ``--backoff-base`` and ``--backoff-max``: Exponential retry backoff controls

Legacy compatibility options are still accepted for now:

* ``--robust``: Deprecated alias for ``--mode safe``
* ``--resume-mode {off,product}``: Deprecated legacy resume selector

Listing Products
----------------

You can list products either with the subcommand form:

.. code-block:: bash

   phidown list --collection SENTINEL-2 --product-type S2MSI2A --bbox 10 45 12 46 --start-date 2024-05-01T00:00:00 --end-date 2024-05-31T23:59:59

or with the main command:

.. code-block:: bash

   phidown --list --collection SENTINEL-2 --product-type S2MSI2A --bbox 10 45 12 46 --start-date 2024-05-01T00:00:00 --end-date 2024-05-31T23:59:59

Listing requires:

* One spatial filter: ``--aoi-wkt`` or ``--bbox``
* At least one temporal filter: ``--start-date`` or ``--end-date``

Useful listing options:

* ``--collection``: Collection name, default ``SENTINEL-1``
* ``--product-type``: Product type filter
* ``--orbit-direction``: ``ASCENDING`` or ``DESCENDING``
* ``--cloud-cover``: Optical cloud threshold
* ``--top``: Maximum number of results
* ``--order-by``: OData sort expression
* ``--format {table,json,csv}``: Output format
* ``--columns``: Comma-separated column selection
* ``--save``: Save output to a file

Burst Coverage Analysis
-----------------------

Run Sentinel-1 burst coverage analysis over an AOI and date range:

.. code-block:: bash

   phidown --burst-coverage --bbox 10 45 12 46 --start-date 2024-08-02T00:00:00 --end-date 2024-08-20T23:59:59 --polarisation VV

Burst coverage requires:

* One spatial filter: ``--aoi-wkt`` or ``--bbox``
* Both ``--start-date`` and ``--end-date``

Useful burst options:

* ``--polarisation {VV,VH,HH,HV}``
* ``--orbit-direction {ASCENDING,DESCENDING}``
* ``--relative-orbit-number``
* ``--preferred-subswath`` such as ``IW1,IW2,IW3``
* ``--format {table,json,csv}``
* ``--columns`` and ``--save``

Examples
--------

List selected columns as CSV:

.. code-block:: bash

   phidown list \
     --collection SENTINEL-1 \
     --product-type SLC \
     --bbox 10 45 12 46 \
     --start-date 2024-08-01T00:00:00 \
     --end-date 2024-08-31T23:59:59 \
     --columns Name,S3Path,ContentDate \
     --format csv \
     --save ./outputs/s1_list.csv

Run a resumable download:

.. code-block:: bash

   phidown \
     --name S1A_IW_GRDH_1SDV_20240503T031926_20240503T031942_053701_0685FB_E003 \
     -o ./data \
     --mode safe

Show help and version:

.. code-block:: bash

   phidown --help
   phidown --version
