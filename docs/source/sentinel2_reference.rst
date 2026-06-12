Sentinel-2 Reference Guide
==========================

This reference guide provides detailed information about Sentinel-2 MSI data parameters and options available through the Copernicus Data Space Ecosystem.

Overview
--------

Sentinel-2 is a constellation of two polar-orbiting satellites (Sentinel-2A and Sentinel-2B) carrying a Multi-Spectral Instrument (MSI). The mission provides high-resolution optical imagery for land monitoring, emergency response, and climate change studies.

**Key Features:**
- Multi-Spectral Instrument (MSI) with 13 spectral bands
- 10m, 20m, and 60m spatial resolution depending on spectral band
- 290 km swath width
- 5-day revisit time (constellation)
- Global coverage with systematic acquisitions over land and coastal areas

Search Parameters
-----------------

**Parameter Types**

When searching for Sentinel-2 data, parameters are passed in two ways:

1. **Direct Parameters:** Passed directly to the ``query_by_filter()`` method
   - ``collection_name`` - Mission/collection identifier
   - ``product_type`` - Product type (S2MSI1C, S2MSI2A, etc.)
   - ``orbit_direction`` - Orbit direction (ASCENDING/DESCENDING)
   - ``aoi_wkt`` - Area of interest in WKT format
   - ``start_date`` / ``end_date`` - Temporal range
   - ``top`` - Maximum number of results

2. **Attributes Dictionary**

   Attributes are passed in the ``attributes`` parameter dictionary. All values listed below have been
   comprehensively tested and verified against the Copernicus Data Space OData API.

   .. table:: Sentinel-2 Attribute Reference
      :widths: 28 42 30

      ============================  ==========================================  ===============================
      Attribute                     Verified Values                             Description
      ============================  ==========================================  ===============================
      ``platformSerialIdentifier``  ``'A'``, ``'B'``                            Satellite platform identifier
      ``instrumentShortName``       ``'MSI'``                                   Multi-Spectral Instrument
      ``tileId``                    MGRS tile (e.g., ``'32TQM'``, ``'33TWG'``) Tile identifier (UTM grid)
      ``operationalMode``           ``'INS-NOBS'``, ``'INS-RAW'``, ``'INS-VIC'`` Instrument operational mode
      ``orbitNumber``               Integer as string                           Absolute orbit number
      ``relativeOrbitNumber``       ``'1'``–``'143'`` (string)                  Relative orbit (repeat cycle)
      ``processingBaseline``        Version string (e.g., ``'05.09'``)          Processing baseline version
      ``qualityStatus``             ``'PASSED'``, ``'FAILED'``, ``'DEGRADED'``  Product quality assessment
      ``sourceProduct``             Product identifier string                   Source L1C product (for L2A)
      ============================  ==========================================  ===============================

   .. note::
      **Processing Level Filtering**
      
      Use ``product_type`` for processing-level selection. phidown accepts common aliases
      such as ``'L1C'``/``'Level-1C'`` and ``'L2A'``/``'Level-2A'``, then sends the
      canonical CDSE identifiers:
      
      - ``'S2MSI1C'`` for Level-1C (Top-of-Atmosphere reflectance)
      - ``'S2MSI2A'`` for Level-2A (Bottom-of-Atmosphere reflectance)
      - ``'S2MSI2B'`` for Level-2B (archived format)

      If ``processingLevel`` or ``productType`` is supplied in ``attributes``,
      the same Sentinel-2 aliases are normalized, but ``product_type`` is clearer.

3. **Method Parameters**

   These parameters are passed directly to ``query_by_filter()``, not in the attributes dictionary:
   
   - ``cloud_cover_threshold`` - Maximum cloud cover percentage (0-100, uses < comparison)
   - ``orbit_direction`` - Orbit direction (``'ASCENDING'`` or ``'DESCENDING'``)
   - ``product_type`` - Product level (``'S2MSI1C'``, ``'S2MSI2A'``, ``'S2MSI2B'``)

Basic Parameters
^^^^^^^^^^^^^^^^

Collection Name
"""""""""""""""
Use ``'SENTINEL-2'`` as the collection name.

.. code-block:: python

   searcher.query_by_filter(collection_name='SENTINEL-2')
   results = searcher.execute_query()

Geographic Parameters
^^^^^^^^^^^^^^^^^^^^^

Geometry
""""""""
Region of Interest defined in Well Known Text (WKT) format with coordinates in decimal degrees (EPSG:4326).

.. code-block:: python

   # Polygon example
   aoi_wkt = 'POLYGON((12.4 41.9, 12.5 41.9, 12.5 42.0, 12.4 42.0, 12.4 41.9))'
   searcher.query_by_filter(
       collection_name='SENTINEL-2',
       aoi_wkt=aoi_wkt
   )
   results = searcher.execute_query()

Tile Identifier
"""""""""""""""
Sentinel-2 data is organized in tiles following the Military Grid Reference System (MGRS). Tile IDs follow the pattern: UTM zone (2 digits) + latitude band (1 letter) + square identifier (2 letters).

.. code-block:: python

   # Search for specific tile
   searcher.query_by_filter(
       collection_name='SENTINEL-2',
       attributes={'tileId': '32TQM'}
   )
   results = searcher.execute_query()

Product Parameters
^^^^^^^^^^^^^^^^^^

Product Types
"""""""""""""
Sentinel-2 offers various product types:

.. table:: Sentinel-2 Product Types
    :widths: 20 60 20
    :header-rows: 1

    * - Category
      - Description
      - Identifier
    * - **Level-1C**
      - **Top-of-Atmosphere (TOA) reflectance:** Orthorectified TOA reflectance with cloud and land/water masks. Most common product for general use.
      - ``S2MSI1C``
    * - **Level-2A**
      - **Bottom-of-Atmosphere (BOA) reflectance:** Atmospherically corrected surface reflectance with cloud and land/water masks.
      - ``S2MSI2A``
    * - **Auxiliary Data**
      - **Supporting data:** Various auxiliary data files including orbit information, calibration parameters, and processing parameters.
      - ``AUX_GNSSRD``, ``AUX_PROQUA``, ``AUX_POEORB``, ``AUX_UT1UTC``
    * - **Ground Image Processing Parameters**
      - **Processing parameters:** Configuration files for various processing steps.
      - ``GIP_*`` (various types)

.. code-block:: python

   # Search for Level-1C products
   searcher.query_by_filter(
       collection_name='SENTINEL-2',
       product_type='S2MSI1C'
   )
   results = searcher.execute_query()

Processing Level
""""""""""""""""
Available processing-level product types:

* ``S2MSI1C`` - Level-1C (Top-of-Atmosphere reflectance)
* ``S2MSI2A`` - Level-2A (Bottom-of-Atmosphere reflectance)
* ``S2MSI2B`` - Level-2B (archived format)

.. code-block:: python

   # Search for Level-2A products
   searcher.query_by_filter(
       collection_name='SENTINEL-2',
       product_type='S2MSI2A'
   )
   results = searcher.execute_query()

Platform Serial Identifier
""""""""""""""""""""""""""
Sentinel-2 constellation satellites:

* ``A`` - Sentinel-2A (launched 2015)
* ``B`` - Sentinel-2B (launched 2017)

.. code-block:: python

   # Search for Sentinel-2A data only
   searcher.query_by_filter(
       collection_name='SENTINEL-2',
       attributes={'platformSerialIdentifier': 'A'}
   )
   results = searcher.execute_query()

Instrument Short Name
"""""""""""""""""""""
* ``MSI`` - Multi-Spectral Instrument (main optical instrument)

.. code-block:: python

   # Search for MSI instrument data
   searcher.query_by_filter(
       collection_name='SENTINEL-2',
       attributes={'instrumentShortName': 'MSI'}
   )
   results = searcher.execute_query()

Sensor Mode
"""""""""""
Sentinel-2 sensor modes:

* ``INS-NOBS`` - Instrument Normal Observation mode
* ``INS-RAW`` - Instrument Raw mode
* ``INS-VIC`` - Instrument Vicarious Calibration mode

.. code-block:: python

   # Search for normal observation mode
   searcher.query_by_filter(
       collection_name='SENTINEL-2',
       attributes={'operationalMode': 'INS-NOBS'}
   )
   results = searcher.execute_query()

Cloud Cover
^^^^^^^^^^^

Cloud Cover Percentage
""""""""""""""""""""""
Filter products by cloud cover percentage (0-100%) using the ``cloud_cover_threshold`` parameter (not in attributes dict).

.. code-block:: python

   # Search for products with less than 20% cloud cover
   searcher = CopernicusDataSearcher()
   searcher.query_by_filter(
       collection_name='SENTINEL-2',
       product_type='S2MSI1C',
       start_date='2016-01-01',
       end_date='2016-12-31',
       cloud_cover_threshold=20,
       top=10
   )
   results = searcher.execute_query()

   # Note: cloud_cover_threshold uses 'less than' comparison (<)
   # Use cloud_cover_threshold=20 to get products with cloudCover < 20

Orbit Parameters
^^^^^^^^^^^^^^^^

Orbit Direction
"""""""""""""""
* ``ASCENDING`` - Satellite moving from south to north
* ``DESCENDING`` - Satellite moving from north to south

.. code-block:: python

   searcher.query_by_filter(
       collection_name='SENTINEL-2',
       orbit_direction='DESCENDING'
   )
   results = searcher.execute_query()

Orbit Number
""""""""""""
Absolute orbit number (integer value or range).

.. code-block:: python

   # Single orbit
   searcher.query_by_filter(
       collection_name='SENTINEL-2',
       attributes={'orbitNumber': '12345'}
   )
   results = searcher.execute_query()

   # Orbit range
   searcher.query_by_filter(
       collection_name='SENTINEL-2',
       attributes={'orbitNumber': '[12345,12350]'}
   )
   results = searcher.execute_query()

Relative Orbit Number
"""""""""""""""""""""
Relative orbit number (1-143 for Sentinel-2), representing the orbit within a repeat cycle.

.. code-block:: python

   # Search for relative orbit 51
   searcher.query_by_filter(
       collection_name='SENTINEL-2',
       attributes={'relativeOrbitNumber': '51'}
   )
   results = searcher.execute_query()

Quality and Processing
^^^^^^^^^^^^^^^^^^^^^^

Processing Baseline
"""""""""""""""""""
Processing baseline version (affects product quality and algorithms used).

.. code-block:: python

   # Search for specific processing baseline
   searcher.query_by_filter(
       collection_name='SENTINEL-2',
       attributes={'processingBaseline': '04.00'}
   )
   results = searcher.execute_query()

   # Search for baseline range
   searcher.query_by_filter(
       collection_name='SENTINEL-2',
       attributes={'processingBaseline': '[04.00,05.00]'}
   )
   results = searcher.execute_query()

Status
""""""
Product availability status:

* ``ONLINE`` - Immediately available for download
* ``OFFLINE`` - Requires retrieval from long-term storage
* ``ALL`` - Both online and offline products

.. code-block:: python

   # Search for immediately available products
   searcher.query_by_filter(
       collection_name='SENTINEL-2',
       attributes={'status': 'ONLINE'}
   )
   results = searcher.execute_query()

Mission Take ID
"""""""""""""""
Mission take identifier for specific acquisition sessions.

.. code-block:: python

   # Search for specific mission take
   searcher.query_by_filter(
       collection_name='SENTINEL-2',
       attributes={'missionTakeId': 'GS2A_20230601T101030_000123_N04.00'}
   )
   results = searcher.execute_query()

Practical Examples
------------------

Example 1: Basic Level-1C Search
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from phidown import CopernicusDataSearcher

   # Search for Level-1C products with low cloud cover
   searcher = CopernicusDataSearcher()
   searcher.query_by_filter(
       collection_name='SENTINEL-2',
       product_type='S2MSI1C',
       aoi_wkt='POLYGON((12.4 41.9, 12.5 41.9, 12.5 42.0, 12.4 42.0, 12.4 41.9))',
       start_date='2023-06-01',
       end_date='2023-06-30',
       cloud_cover_threshold=20,
       top=10
   )
   results = searcher.execute_query()
   
   print(f"Found {len(results)} Level-1C products with <20% cloud cover")

Example 2: Level-2A Surface Reflectance
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from phidown import CopernicusDataSearcher

   searcher = CopernicusDataSearcher()
   
   # Search for atmospherically corrected Level-2A products
   searcher.query_by_filter(
       collection_name='SENTINEL-2',
       product_type='S2MSI2A',
       aoi_wkt='POLYGON((12.4 41.9, 12.5 41.9, 12.5 42.0, 12.4 42.0, 12.4 41.9))',
       start_date='2023-06-01',
       end_date='2023-06-30',
       cloud_cover_threshold=10,
       top=10
   )
   results = searcher.execute_query()
   
   print(f"Found {len(results)} Level-2A products")

Example 3: Specific Tile Search
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from phidown import CopernicusDataSearcher

   searcher = CopernicusDataSearcher()
   
   # Search for specific tile over time
   searcher.query_by_filter(
       collection_name='SENTINEL-2',
       product_type='S2MSI1C',
       start_date='2023-01-01',
       end_date='2023-12-31',
       cloud_cover_threshold=30,
       attributes={'tileId': '32TQM'}
   )
   results = searcher.execute_query()
   
   print(f"Found {len(results)} products for tile 32TQM")

Example 4: Time Series Analysis
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from phidown import CopernicusDataSearcher
   import pandas as pd

   searcher = CopernicusDataSearcher()
   
   # Search for consistent time series data
   searcher.query_by_filter(
       collection_name='SENTINEL-2',
       product_type='S2MSI1C',
       start_date='2023-01-01',
       end_date='2023-12-31',
       cloud_cover_threshold=20,
       attributes={
           'tileId': '32TQM',
           'relativeOrbitNumber': '51'
       }
   )
   results = searcher.execute_query()
   
   # Group by date to analyze temporal coverage
   results['Date'] = pd.to_datetime(results['ContentDate']).dt.date
   temporal_coverage = results.groupby('Date').size()
   
   print(f"Found {len(results)} products over {len(temporal_coverage)} unique dates")

Example 5: Multi-Platform Comparison
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from phidown import CopernicusDataSearcher

   searcher = CopernicusDataSearcher()
   
   # Compare data from both Sentinel-2A and Sentinel-2B
   searcher.query_by_filter(
       collection_name='SENTINEL-2',
       product_type='S2MSI1C',
       aoi_wkt='POLYGON((12.4 41.9, 12.5 41.9, 12.5 42.0, 12.4 42.0, 12.4 41.9))',
       start_date='2023-06-01',
       end_date='2023-06-30',
       cloud_cover_threshold=15,
       attributes={'platformSerialIdentifier': 'A'}
   )
   s2a_results = searcher.execute_query()
   
   searcher.query_by_filter(
       collection_name='SENTINEL-2',
       product_type='S2MSI1C',
       aoi_wkt='POLYGON((12.4 41.9, 12.5 41.9, 12.5 42.0, 12.4 42.0, 12.4 41.9))',
       start_date='2023-06-01',
       end_date='2023-06-30',
       cloud_cover_threshold=15,
       attributes={'platformSerialIdentifier': 'B'}
   )
   s2b_results = searcher.execute_query()
   
   print(f"Sentinel-2A: {len(s2a_results)} products")
   print(f"Sentinel-2B: {len(s2b_results)} products")

Example 6: Processing Baseline Filtering
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from phidown import CopernicusDataSearcher

   searcher = CopernicusDataSearcher()
   
   # Search for products with latest processing baseline
   searcher.query_by_filter(
       collection_name='SENTINEL-2',
       product_type='S2MSI2A',
       aoi_wkt='POLYGON((12.4 41.9, 12.5 41.9, 12.5 42.0, 12.4 42.0, 12.4 41.9))',
       start_date='2023-06-01',
       end_date='2023-06-30',
       cloud_cover_threshold=25,
       attributes={'processingBaseline': '[04.00,05.00]'}
   )
   results = searcher.execute_query()
   
   print(f"Found {len(results)} products with processing baseline 4.00-5.00")

Search Optimization Tips
------------------------

1. **Use Tile IDs:** For specific areas, use tile IDs rather than large polygons for better performance.

2. **Filter by Cloud Cover:** Always set appropriate cloud cover thresholds for your application.

3. **Choose Processing Level:** Use Level-1C for general applications, Level-2A for surface analysis.

4. **Consider Processing Baseline:** Newer baselines provide better quality but may not be available for all historical data.

5. **Optimize Temporal Range:** Use appropriate date ranges to balance between data availability and search performance.

6. **Use Relative Orbit Numbers:** For consistent geometry in time series analysis.

7. **Check Product Status:** Use ``attributes={'status': 'ONLINE'}`` for immediate download needs.

Common Use Cases
----------------

**Land Applications:**
- Vegetation monitoring: Level-2A, low cloud cover
- Crop mapping: Level-1C or Level-2A, growing season
- Land cover classification: Level-2A, multi-temporal
- Deforestation monitoring: Level-1C, specific tiles

**Water Applications:**
- Water quality monitoring: Level-2A, clear conditions
- Coastal monitoring: Level-1C, coastal tiles
- Lake/reservoir monitoring: Level-2A, specific areas

**Urban Applications:**
- Urban expansion monitoring: Level-1C, consistent orbit
- Infrastructure monitoring: Level-1C, high spatial resolution bands
- Heat island studies: Level-2A, thermal considerations

**Agricultural Applications:**
- Crop health monitoring: Level-2A, vegetation indices
- Yield prediction: Level-1C/2A, time series
- Irrigation mapping: Level-2A, SWIR bands

**Environmental Applications:**
- Wildfire monitoring: Level-1C, near real-time
- Drought monitoring: Level-2A, vegetation stress
- Biodiversity studies: Level-2A, habitat mapping

Technical Specifications
-------------------------

**Spectral Bands:**
- Band 1 (Coastal aerosol): 443 nm, 60m
- Band 2 (Blue): 490 nm, 10m
- Band 3 (Green): 560 nm, 10m
- Band 4 (Red): 665 nm, 10m
- Band 5 (Vegetation Red Edge): 705 nm, 20m
- Band 6 (Vegetation Red Edge): 740 nm, 20m
- Band 7 (Vegetation Red Edge): 783 nm, 20m
- Band 8 (NIR): 842 nm, 10m
- Band 8A (Vegetation Red Edge): 865 nm, 20m
- Band 9 (Water vapour): 945 nm, 60m
- Band 10 (SWIR – Cirrus): 1375 nm, 60m
- Band 11 (SWIR): 1610 nm, 20m
- Band 12 (SWIR): 2190 nm, 20m

**Orbital Characteristics:**
- Altitude: 786 km
- Inclination: 98.62°
- Repeat cycle: 10 days (single satellite)
- Revisit time: 5 days (constellation)
- Swath width: 290 km

**Radiometric Performance:**
- Radiometric resolution: 12 bits
- Signal-to-noise ratio: >100 for most bands
- Radiometric accuracy: <3% (reflectance)

For more detailed information about Sentinel-2 specifications and applications, refer to the official ESA Sentinel-2 documentation.
