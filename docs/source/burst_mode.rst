Burst Mode: Sentinel-1 SLC Burst Search and Download
=====================================================

Overview
--------

Phidown provides comprehensive support for searching and downloading individual Sentinel-1 SLC bursts. This feature allows you to access the fundamental imaging units of Sentinel-1 TOPSAR data without downloading entire SLC products.

What are Sentinel-1 Bursts?
----------------------------

Sentinel-1 operates in Interferometric Wide (IW) and Extra-Wide (EW) modes using a ScanSAR technique called TOPSAR (Terrain Observation with Progressive Scans SAR). In these modes, the radar antenna repeatedly switches between several adjacent sub-swaths, collecting short sequences of radar pulses during each observation. Each of these short pulse sequences is known as a **burst**, which represents the smallest imaging unit in Sentinel-1 SLC data.

A standard IW or EW SLC product combines data from many bursts. Each sub-swath is processed into an image containing a series of slightly overlapping bursts, and all sub-swaths (three for IW, five for EW) are then merged to form the final SLC product. Although the product contains multiple bursts, each burst can also be processed and used individually.

Key Characteristics
~~~~~~~~~~~~~~~~~~~

- **Available from**: August 2, 2024 onwards
- **IW Mode**: 3 sub-swaths (IW1, IW2, IW3)
- **EW Mode**: 5 sub-swaths (EW1, EW2, EW3, EW4, EW5)
- **Polarizations**: VV, VH, HH, HV
- **On-Demand Processing**: Bursts are generated dynamically upon request

Searching for Bursts
---------------------

Enabling Burst Mode
~~~~~~~~~~~~~~~~~~~

To search for bursts instead of full products, set ``burst_mode=True`` in the ``query_by_filter`` method:

.. code-block:: python

    from phidown.search import CopernicusDataSearcher

    searcher = CopernicusDataSearcher()
    searcher.query_by_filter(
        burst_mode=True,
        start_date='2024-08-01T00:00:00',
        end_date='2024-08-03T00:00:00',
        top=10
    )

    df = searcher.execute_query()

Available Burst Parameters
~~~~~~~~~~~~~~~~~~~~~~~~~~

When ``burst_mode=True``, you can use the following burst-specific filters:

.. list-table::
   :header-rows: 1
   :widths: 20 15 40 25

   * - Parameter
     - Type
     - Description
     - Example Values
   * - ``burst_id``
     - int
     - Unique identifier for a specific burst location
     - ``15804``
   * - ``absolute_burst_id``
     - int
     - Global unique burst identifier
     - ``1580415``
   * - ``swath_identifier``
     - str
     - Swath name
     - ``'IW1'``, ``'IW2'``, ``'IW3'``, ``'EW1'``-``'EW5'``
   * - ``parent_product_name``
     - str
     - Name of the parent SLC product
     - ``'S1A_IW_SLC__1SDV_...'``
   * - ``parent_product_type``
     - str
     - Type of parent product
     - ``'IW_SLC__1S'``, ``'EW_SLC__1S'``
   * - ``operational_mode``
     - str
     - Acquisition mode
     - ``'IW'``, ``'EW'``
   * - ``polarisation_channels``
     - str
     - Polarization
     - ``'VV'``, ``'VH'``, ``'HH'``, ``'HV'``
   * - ``platform_serial_identifier``
     - str
     - Sentinel-1 satellite
     - ``'A'``, ``'B'``
   * - ``relative_orbit_number``
     - int
     - Relative orbit number
     - ``8``, ``73``
   * - ``datatake_id``
     - int
     - Datatake identifier
     - ``439374``

You can also combine burst-specific parameters with standard filters like ``start_date``, ``end_date``, ``aoi_wkt``, and ``orbit_direction``.

Search Examples
---------------

Example 1: Basic Burst Search with Temporal Filter
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The simplest burst search uses only temporal filters:

.. code-block:: python

    from phidown.search import CopernicusDataSearcher

    searcher = CopernicusDataSearcher()

    # Configure search for bursts with temporal filter
    searcher.query_by_filter(
        burst_mode=True,
        start_date='2024-08-01T00:00:00',
        end_date='2024-08-03T00:00:00',
        top=10,
        count=True
    )

    # Execute the query
    df = searcher.execute_query()
    print(f'Number of results: {len(df)}')
    print(f'Total available results: {searcher.num_results}')

    # Display first few results
    searcher.display_results(top_n=5)

Example 2: Burst Search with Spatial Filter (AOI)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Combine burst mode with spatial filtering using a WKT polygon:

.. code-block:: python

    # Define an area of interest (example: region in central Europe)
    aoi_wkt = """POLYGON((12.655118166047592 47.44667197521409, 
                           21.39065656328509 48.347694733853245, 
                           28.334291357162826 41.877123516783655, 
                           17.47086198383573 40.35854475076158, 
                           12.655118166047592 47.44667197521409))"""

    searcher = CopernicusDataSearcher()

    # Configure search with AOI and temporal filter
    searcher.query_by_filter(
        burst_mode=True,
        aoi_wkt=aoi_wkt,
        start_date='2024-08-01T00:00:00',
        end_date='2024-08-03T00:00:00',
        top=10,
        count=True
    )

    # Execute and display results
    df = searcher.execute_query()
    print(f'Found {len(df)} bursts in the specified area')

Example 3: Search by Specific Burst ID
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve all acquisitions of a specific burst:

.. code-block:: python

    searcher = CopernicusDataSearcher()

    # Search for a specific burst ID
    searcher.query_by_filter(
        burst_mode=True,
        burst_id=15804,
        start_date='2024-08-01T00:00:00',
        end_date='2024-08-15T00:00:00',
        top=20,
        count=True
    )

    df = searcher.execute_query()
    print(f'Found {len(df)} acquisitions of burst 15804')

Example 4: Filter by Swath and Polarization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Search for bursts from a specific swath with specific polarization:

.. code-block:: python

    searcher = CopernicusDataSearcher()

    # Search for IW2 swath with VV polarization
    searcher.query_by_filter(
        burst_mode=True,
        swath_identifier='IW2',
        polarisation_channels='VV',
        start_date='2024-08-01T00:00:00',
        end_date='2024-08-03T00:00:00',
        top=10,
        count=True
    )

    df = searcher.execute_query()
    print(f'Found {len(df)} bursts from swath IW2 with VV polarization')

Example 5: Search Bursts from a Specific Parent Product
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve all bursts from a specific parent SLC product:

.. code-block:: python

    searcher = CopernicusDataSearcher()

    parent_product = 'S1A_IW_SLC__1SDV_20240802T060719_20240802T060746_055030_06B44E_E7CC.SAFE'

    searcher.query_by_filter(
        burst_mode=True,
        parent_product_name=parent_product,
        start_date='2024-08-01T00:00:00',
        end_date='2024-08-15T00:00:00',
        polarisation_channels='VV',
        top=1000
    )

    df = searcher.execute_query()
    print(f'Found {len(df)} bursts in parent product')

Example 6: Filter by Orbit Parameters
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Combine orbit parameters for consistent time-series analysis:

.. code-block:: python

    searcher = CopernicusDataSearcher()

    searcher.query_by_filter(
        burst_mode=True,
        orbit_direction='DESCENDING',
        relative_orbit_number=8,
        operational_mode='IW',
        start_date='2024-08-01T00:00:00',
        end_date='2024-08-10T00:00:00',
        top=20,
        count=True
    )

    df = searcher.execute_query()
    print(f'Found {len(df)} bursts from descending orbit #8')

Example 7: Advanced Multi-Parameter Search
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Combine multiple parameters for highly targeted searches:

.. code-block:: python

    searcher = CopernicusDataSearcher()

    searcher.query_by_filter(
        burst_mode=True,
        burst_id=15804,
        swath_identifier='IW2',
        parent_product_type='IW_SLC__1S',
        orbit_direction='DESCENDING',
        relative_orbit_number=8,
        operational_mode='IW',
        polarisation_channels='VV',
        platform_serial_identifier='A',  # Sentinel-1A
        start_date='2024-08-01T00:00:00',
        end_date='2024-08-15T00:00:00',
        top=20,
        count=True
    )

    df = searcher.execute_query()
    print(f'Found {len(df)} bursts matching all criteria')

Downloading Bursts
------------------

Authentication
~~~~~~~~~~~~~~

To download bursts, you need to obtain an access token using your CDSE credentials:

.. code-block:: python

    from phidown.downloader import get_token

    access_token = get_token(
        username='your_cdse_username',
        password='your_cdse_password'
    )

On-Demand Burst Download
~~~~~~~~~~~~~~~~~~~~~~~~~

Bursts are generated on-demand rather than retrieved from pre-stored files. This means S3 commands are not applicable. Instead, a POST request is sent to the CDSE service, which dynamically produces and returns the requested burst.

.. code-block:: python

    from pathlib import Path
    from phidown.downloader import download_burst_on_demand

    # Get burst ID from search results
    burst_id = df.iloc[0]['Id']

    # Download the burst
    download_burst_on_demand(
        burst_id=burst_id,
        token=access_token,
        output_dir=Path('./output')
    )

Complete Download Workflow
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Here's a complete example combining search and download:

.. code-block:: python

    import os
    from pathlib import Path
    from phidown.search import CopernicusDataSearcher
    from phidown.downloader import get_token, download_burst_on_demand

    # Step 1: Authenticate
    username = os.environ['CDSE_USERNAME']
    password = os.environ['CDSE_PASSWORD']
    token = get_token(username=username, password=password)

    # Step 2: Search for bursts
    searcher = CopernicusDataSearcher()
    searcher.query_by_filter(
        burst_mode=True,
        burst_id=15804,
        swath_identifier='IW2',
        polarisation_channels='VV',
        start_date='2024-08-01T00:00:00',
        end_date='2024-08-03T00:00:00',
        top=5
    )
    df = searcher.execute_query()

    # Step 3: Download bursts
    output_dir = Path('./bursts')
    output_dir.mkdir(exist_ok=True)

    for idx, row in df.iterrows():
        burst_id = row['Id']
        print(f'Downloading burst {burst_id}...')
        download_burst_on_demand(
            burst_id=burst_id,
            token=token,
            output_dir=output_dir
        )

Common Use Cases
----------------

InSAR Time Series
~~~~~~~~~~~~~~~~~

Search for specific burst IDs across multiple dates with consistent orbit parameters:

.. code-block:: python

    searcher.query_by_filter(
        burst_mode=True,
        burst_id=15804,
        relative_orbit_number=8,
        orbit_direction='DESCENDING',
        start_date='2024-08-01T00:00:00',
        end_date='2024-12-31T00:00:00',
        top=1000
    )

Regional Analysis
~~~~~~~~~~~~~~~~~

Use AOI with swath/polarization filters to get bursts covering your study area:

.. code-block:: python

    searcher.query_by_filter(
        burst_mode=True,
        aoi_wkt=your_polygon_wkt,
        swath_identifier='IW2',
        polarisation_channels='VV',
        start_date='2024-08-01T00:00:00',
        end_date='2024-08-31T00:00:00'
    )

Product Decomposition
~~~~~~~~~~~~~~~~~~~~~

Retrieve all bursts from a parent SLC product for individual processing:

.. code-block:: python

    searcher.query_by_filter(
        burst_mode=True,
        parent_product_name='S1A_IW_SLC__1SDV_...',
        top=1000
    )

Systematic Monitoring
~~~~~~~~~~~~~~~~~~~~~

Filter by relative orbit number and burst ID for regular acquisitions:

.. code-block:: python

    searcher.query_by_filter(
        burst_mode=True,
        burst_id=15804,
        relative_orbit_number=8,
        start_date='2024-08-01T00:00:00',
        end_date='2024-12-31T00:00:00'
    )

Valid Parameter Values
----------------------

**Swath Identifiers**
  - IW mode: ``'IW1'``, ``'IW2'``, ``'IW3'``
  - EW mode: ``'EW1'``, ``'EW2'``, ``'EW3'``, ``'EW4'``, ``'EW5'``

**Parent Product Types**
  - ``'IW_SLC__1S'`` (Interferometric Wide SLC)
  - ``'EW_SLC__1S'`` (Extra Wide SLC)

**Operational Modes**
  - ``'IW'`` (Interferometric Wide)
  - ``'EW'`` (Extra Wide)

**Polarization Channels**
  - ``'VV'`` (Vertical-Vertical)
  - ``'VH'`` (Vertical-Horizontal)
  - ``'HH'`` (Horizontal-Horizontal)
  - ``'HV'`` (Horizontal-Vertical)

**Platform Serial Identifiers**
  - ``'A'`` (Sentinel-1A)
  - ``'B'`` (Sentinel-1B)

**Orbit Directions**
  - ``'ASCENDING'``
  - ``'DESCENDING'``

Important Notes
---------------

.. note::
   Burst data is only available from **August 2, 2024** onwards.

.. warning::
   Bursts are generated **on-demand**, which means download times may be longer than for pre-stored products. The first request for a specific burst may take several minutes as the system processes it.

.. tip::
   For InSAR time series, always use the same ``burst_id`` and ``relative_orbit_number`` to ensure spatial consistency across acquisitions.

.. seealso::
   - `Copernicus Data Space Ecosystem <https://dataspace.copernicus.eu/>`_
   - `CDSE Burst Processing Documentation <https://github.com/eu-cdse/notebook-samples/blob/main/geo/bursts_processing_on_demand.ipynb>`_
   - :doc:`search` for general search functionality
   - :doc:`download` for standard product downloads

API Reference
-------------

.. autofunction:: phidown.downloader.get_token

.. autofunction:: phidown.downloader.download_burst_on_demand

.. automethod:: phidown.search.CopernicusDataSearcher.query_by_filter
   :noindex:
