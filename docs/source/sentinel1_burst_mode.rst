Sentinel-1 SLC Burst Mode
==========================

.. contents:: Table of Contents
   :depth: 3
   :local:

Overview
--------

Sentinel-1 SLC Burst Mode allows you to search for and access individual radar bursts from Sentinel-1 Single Look Complex (SLC) products without downloading entire scenes. This feature is particularly useful for InSAR time series analysis, regional studies, and efficient data access.

**Key Benefits:**

- Access individual bursts instead of full SLC products (typically 1-2 GB per burst vs 5-8 GB per product)
- Search by specific burst IDs for consistent time series
- Filter by swath, polarization, and orbit parameters
- Combine with spatial (AOI) and temporal filters
- Available for data from August 2, 2024 onwards

What are Sentinel-1 Bursts?
----------------------------

Sentinel-1 SLC products are composed of multiple bursts - individual radar acquisitions captured during a satellite pass. Each burst represents a specific geographic area with the following characteristics:

**Burst Properties:**

- **Burst ID**: Unique integer identifier for a specific burst location
- **Absolute Burst ID**: Global unique identifier across all Sentinel-1 data
- **Swath**: Part of the imaging swath (IW1, IW2, IW3 for Interferometric Wide; EW1-EW5 for Extra Wide)
- **Coverage**: Each burst covers approximately 20-25 km in azimuth direction
- **Overlap**: Adjacent bursts overlap to ensure continuous coverage

**Parent Product Structure:**

.. code-block:: text

    Sentinel-1 SLC Product (e.g., IW mode)
    ├── IW1 Swath
    │   ├── Burst 1
    │   ├── Burst 2
    │   └── ...
    ├── IW2 Swath
    │   ├── Burst 1
    │   ├── Burst 2
    │   └── ...
    └── IW3 Swath
        ├── Burst 1
        ├── Burst 2
        └── ...

Getting Started
---------------

Basic Burst Search
~~~~~~~~~~~~~~~~~~

To search for bursts, set ``burst_mode=True`` in the ``query_by_filter()`` method:

.. code-block:: python

    from phidown.search import CopernicusDataSearcher
    
    # Create searcher instance
    searcher = CopernicusDataSearcher()
    
    # Search for bursts with temporal filter
    searcher.query_by_filter(
        burst_mode=True,
        start_date='2024-08-01T00:00:00',
        end_date='2024-08-03T00:00:00',
        top=10,
        count=True
    )
    
    # Execute the query
    df = searcher.execute_query()
    print(f'Found {len(df)} bursts')
    print(f'Total available: {searcher.num_results}')
    
    # Display results
    searcher.display_results(top_n=5)

Burst-Specific Parameters
--------------------------

The following parameters are available exclusively in burst mode:

Core Identifiers
~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Parameter
     - Type
     - Description
   * - ``burst_id``
     - int
     - Unique identifier for a specific burst location
   * - ``absolute_burst_id``
     - int
     - Global unique burst identifier across all Sentinel-1 data
   * - ``parent_product_id``
     - str
     - UUID of the parent SLC product
   * - ``parent_product_name``
     - str
     - Name of the parent SLC product (e.g., 'S1A_IW_SLC__1SDV_...')

Swath and Acquisition
~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Parameter
     - Type
     - Description
   * - ``swath_identifier``
     - str
     - Swath name: 'IW1', 'IW2', 'IW3', 'EW1', 'EW2', 'EW3', 'EW4', 'EW5'
   * - ``operational_mode``
     - str
     - Acquisition mode: 'IW' (Interferometric Wide), 'EW' (Extra Wide)
   * - ``parent_product_type``
     - str
     - Parent product type: 'IW_SLC__1S' or 'EW_SLC__1S'

Polarization and Platform
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Parameter
     - Type
     - Description
   * - ``polarisation_channels``
     - str
     - Polarization: 'VV', 'VH', 'HH', 'HV'
   * - ``platform_serial_identifier``
     - str
     - Sentinel-1 satellite: 'A' (Sentinel-1A), 'B' (Sentinel-1B)

Orbit Parameters
~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Parameter
     - Type
     - Description
   * - ``relative_orbit_number``
     - int
     - Relative orbit number (1-175)
   * - ``datatake_id``
     - int
     - Datatake identifier

Common Use Cases
----------------

1. InSAR Time Series Analysis
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Search for the same burst across multiple dates for interferometric analysis:

.. code-block:: python

    # Search for specific burst ID over time
    searcher.query_by_filter(
        burst_mode=True,
        burst_id=15804,
        relative_orbit_number=8,
        orbit_direction='DESCENDING',
        start_date='2024-08-01T00:00:00',
        end_date='2024-09-01T00:00:00',
        top=100,
        count=True
    )
    
    df = searcher.execute_query()
    print(f'Found {len(df)} acquisitions of burst 15804')

2. Regional Coverage Analysis
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Find all bursts covering a specific area of interest:

.. code-block:: python

    # Define area of interest
    aoi_wkt = """POLYGON((12.4 41.8, 12.5 41.8, 
                          12.5 41.9, 12.4 41.9, 
                          12.4 41.8))"""
    
    # Search for bursts intersecting AOI
    searcher.query_by_filter(
        burst_mode=True,
        aoi_wkt=aoi_wkt,
        swath_identifier='IW2',
        polarisation_channels='VV',
        start_date='2024-08-01T00:00:00',
        end_date='2024-08-03T00:00:00',
        top=50
    )
    
    df = searcher.execute_query()

3. Parent Product Decomposition
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve all bursts from a specific SLC product:

.. code-block:: python

    # Get all bursts from a parent product
    parent_product = 'S1A_IW_SLC__1SDV_20240802T060719_20240802T060746_055030_06B44E_E7CC.SAFE'
    
    searcher.query_by_filter(
        burst_mode=True,
        parent_product_name=parent_product,
        start_date='2024-08-01T00:00:00',
        end_date='2024-08-15T00:00:00',
        top=1000
    )
    
    df = searcher.execute_query()
    print(f'Parent product contains {len(df)} bursts')

4. Multi-Parameter Filtering
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Combine multiple criteria for precise searches:

.. code-block:: python

    # Advanced multi-parameter search
    searcher.query_by_filter(
        burst_mode=True,
        burst_id=15804,
        swath_identifier='IW2',
        polarisation_channels='VV',
        orbit_direction='DESCENDING',
        relative_orbit_number=8,
        operational_mode='IW',
        platform_serial_identifier='A',
        start_date='2024-08-01T00:00:00',
        end_date='2024-08-15T00:00:00',
        count=True
    )
    
    df = searcher.execute_query()

Burst Result Structure
----------------------

Burst searches return DataFrames with the following columns:

**Core Metadata:**

- ``Id``: Unique burst identifier (UUID)
- ``Name``: Burst product name
- ``ContentType``: Content type identifier
- ``S3Path``: S3 storage path for the burst

**Burst-Specific Fields:**

- ``BurstId``: Burst ID (integer)
- ``AbsoluteBurstId``: Global burst identifier
- ``SwathIdentifier``: Swath name (IW1/IW2/IW3/EW1-EW5)
- ``PolarisationChannels``: Polarization (VV/VH/HH/HV)
- ``OperationalMode``: Acquisition mode (IW/EW)

**Parent Product Information:**

- ``ParentProductId``: Parent product UUID
- ``ParentProductName``: Parent SLC product name
- ``ParentProductType``: Parent product type

**Orbit and Timing:**

- ``OrbitDirection``: ASCENDING or DESCENDING
- ``RelativeOrbitNumber``: Relative orbit number
- ``PlatformSerialIdentifier``: Satellite (A or B)
- ``ContentDate``: Acquisition date/time
- ``AzimuthTime``: Azimuth time
- ``AzimuthAnxTime``: Azimuth time from ascending node crossing

**Geometric Information:**

- ``Footprint``: WKT footprint geometry
- ``GeoFootprint``: Geographic footprint
- ``ByteOffset``: Byte offset in parent product
- ``Lines``: Number of lines
- ``LinesPerBurst``: Lines per burst
- ``SamplesPerBurst``: Samples per burst

**Temporal Coverage:**

- ``BeginningDateTime``: Burst start time
- ``EndingDateTime``: Burst end time
- ``DatatakeID``: Datatake identifier

Combining with Standard Filters
--------------------------------

Burst mode works seamlessly with standard search parameters:

Temporal Filtering
~~~~~~~~~~~~~~~~~~

.. code-block:: python

    searcher.query_by_filter(
        burst_mode=True,
        start_date='2024-08-01T00:00:00',
        end_date='2024-08-31T23:59:59',
        # ... other burst parameters
    )

Spatial Filtering (AOI)
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    searcher.query_by_filter(
        burst_mode=True,
        aoi_wkt='POLYGON((...)))',  # WKT polygon
        # ... other burst parameters
    )

Orbit Direction
~~~~~~~~~~~~~~~

.. code-block:: python

    searcher.query_by_filter(
        burst_mode=True,
        orbit_direction='DESCENDING',  # or 'ASCENDING'
        # ... other burst parameters
    )

Result Pagination
~~~~~~~~~~~~~~~~~

.. code-block:: python

    searcher.query_by_filter(
        burst_mode=True,
        top=1000,        # Maximum results to return
        count=True,      # Get total count
        order_by='ContentDate/Start desc',  # Sort order
        # ... other burst parameters
    )

Best Practices
--------------

1. **Temporal Coverage**
   
   - Burst data is available from August 2, 2024 onwards
   - Use ``count=True`` to check total available results before downloading

2. **Burst ID Consistency**
   
   - Use the same ``burst_id`` across dates for time series analysis
   - Combine with ``relative_orbit_number`` for guaranteed consistency

3. **Swath Selection**
   
   - IW mode has 3 swaths (IW1, IW2, IW3)
   - EW mode has 5 swaths (EW1, EW2, EW3, EW4, EW5)
   - Central swath (IW2) often provides best coverage

4. **Polarization**
   
   - VV polarization most common for IW mode
   - Check available polarizations: 'VV', 'VH', 'HH', 'HV'

5. **Performance Optimization**
   
   - Use specific burst IDs when known
   - Limit search with ``top`` parameter
   - Apply swath and polarization filters to reduce results

6. **Validation**
   
   - Always validate parameters are within allowed values
   - Use ``count=True`` to verify result counts before processing
   - Check ``searcher.num_results`` for total available bursts

API Endpoint
------------

Burst searches use a different endpoint than standard product searches:

**Burst Endpoint:**

.. code-block:: text

    https://catalogue.dataspace.copernicus.eu/odata/v1/Bursts

**Product Endpoint (standard):**

.. code-block:: text

    https://catalogue.dataspace.copernicus.eu/odata/v1/Products

The library automatically uses the correct endpoint based on the ``burst_mode`` parameter.

Examples Notebook
-----------------

A comprehensive Jupyter notebook with 9 detailed examples is available:

**Location:** ``notebooks/6_burst_search_examples.ipynb``

**Examples Include:**

1. Basic burst search with temporal filter
2. Burst search with spatial filter (AOI)
3. Search by specific Burst ID
4. Filter by swath identifier and polarization
5. Search bursts from parent products
6. Orbit direction and relative orbit filtering
7. Advanced multi-parameter searches
8. Burst result analysis and statistics
9. Visualization of burst footprints

To run the examples:

.. code-block:: bash

    cd notebooks
    jupyter notebook 6_burst_search_examples.ipynb

Troubleshooting
---------------

Common Issues
~~~~~~~~~~~~~

**Issue: No results returned**

- Check date range is after August 2, 2024
- Verify AOI polygon format (WKT with EPSG:4326)
- Confirm burst parameters are valid values

**Issue: Invalid parameter error**

- Check ``swath_identifier`` is one of: IW1, IW2, IW3, EW1-EW5
- Verify ``parent_product_type`` is: IW_SLC__1S or EW_SLC__1S
- Ensure ``operational_mode`` is: IW or EW

**Issue: Date format error**

- Use ISO 8601 format: ``YYYY-MM-DDTHH:MM:SS``
- Do not include ``.000Z`` suffix
- Correct: ``'2024-08-01T00:00:00'``
- Incorrect: ``'2024-08-01T00:00:00.000Z'``

**Issue: Column not found in display_results()**

- Burst mode uses different columns than product mode
- The library automatically selects appropriate columns
- Or specify custom columns: ``searcher.display_results(columns=['BurstId', 'SwathIdentifier'])``

Debugging
~~~~~~~~~

Enable query debugging:

.. code-block:: python

    # View the generated query URL
    print(searcher._build_query())
    
    # Check what columns are available
    if searcher.df is not None:
        print(searcher.df.columns.tolist())
    
    # Verify burst mode is enabled
    print(f'Burst mode: {searcher.burst_mode}')

API Reference
-------------

For detailed API documentation, see:

- :doc:`api_reference` - Complete API documentation
- :doc:`sentinel1_reference` - Sentinel-1 general reference

See Also
--------

- :doc:`examples` - More usage examples
- :doc:`getting_started` - Getting started guide
- :doc:`user_guide` - User guide

External Resources
------------------

- `Copernicus Data Space Ecosystem <https://dataspace.copernicus.eu/>`_
- `Sentinel-1 SLC Burst Announcement <https://dataspace.copernicus.eu/news/2024-11-22-sentinel-1-slc-bursts-are-available-cdse>`_
- `Sentinel-1 Technical Documentation <https://sentinel.esa.int/web/sentinel/technical-guides/sentinel-1-sar>`_
- `InSAR Processing with Bursts <https://step.esa.int/main/doc/tutorials/>`_
