Sentinel-3 Reference Guide
==========================

This reference guide provides detailed information about Sentinel-3 data parameters and options available through the Copernicus Data Space Ecosystem.

Overview
--------

Sentinel-3 is a constellation of two polar-orbiting satellites (Sentinel-3A and Sentinel-3B) carrying multiple instruments for ocean and land monitoring. The mission provides systematic measurements of Earth's oceans, land, ice, and atmosphere.

**Key Features:**
- Ocean and Land Colour Instrument (OLCI) - 21 spectral bands
- Sea and Land Surface Temperature Radiometer (SLSTR) - thermal and optical channels
- SAR Radar Altimeter (SRAL) - precise height measurements
- Synergy products combining OLCI and SLSTR data
- 27-day repeat cycle with daily global coverage
- Systematic global coverage for ocean and land applications

Search Parameters
-----------------

**Parameter Types**

When searching for Sentinel-3 data, parameters are passed in two ways:

1. **Direct Parameters:** Passed directly to the ``search()`` method
   - ``collection_name`` - Mission/collection identifier
   - ``product_type`` - Product type (OL_1_EFR___, OL_2_LFR___, etc.)
   - ``orbit_direction`` - Orbit direction (ASCENDING/DESCENDING)
   - ``aoi_wkt`` - Area of interest in WKT format
   - ``start_date`` / ``end_date`` - Temporal range
   - ``top`` - Maximum number of results

2. **Attributes Dictionary**

   Attributes are passed in the ``attributes`` parameter dictionary. All values listed below have been
   comprehensively tested and verified against the Copernicus Data Space OData API.

   .. table:: Sentinel-3 Attribute Reference
      :widths: 28 42 30

      ============================  ==========================================  ===============================
      Attribute                     Verified Values                             Description
      ============================  ==========================================  ===============================
      ``platformSerialIdentifier``  ``'A'``, ``'B'``                            Satellite platform identifier
      ``instrumentShortName``       ``'OLCI'``, ``'SLSTR'``, ``'SRAL'``         Instrument type
      ``processingLevel``           ``'1'``, ``'2'``                            Processing level (numeric string)
      ``timeliness``                ``'NR'``, ``'NT'``, ``'ST'``                Data delivery timeliness
      ``orbitDirection``            ``'ASCENDING'``, ``'DESCENDING'``           Satellite orbit direction
      ``orbitNumber``               Integer as string                           Absolute orbit number
      ``relativeOrbitNumber``       ``'1'``–``'385'`` (string)                  Relative orbit (27-day cycle)
      ``cycleNumber``               Integer as string                           Mission cycle number
      ``processingBaseline``        Version string (e.g., ``'03.46'``)          Processing baseline version
      ``operationalMode``           ``'EO'`` (Earth Observation)                Operational mode
      ============================  ==========================================  ===============================

   .. important::
      **Processing Level Format**
      
      Sentinel-3 ``processingLevel`` must be specified as:
      
      - ✓ ``'1'`` or ``'2'`` (numeric strings)
      - ✗ NOT ``'L1'``, ``'L2'``, ``'LEVEL1'``, or ``'LEVEL2'``

   .. note::
      **Timeliness Categories**
      
      - ``'NR'`` - Near Real-Time (3 hours)
      - ``'NT'`` - Non-Time-Critical (1 month)
      - ``'ST'`` - Short Time-Critical (48 hours)
      
      Data availability varies by timeliness category and date range.

Basic Parameters
^^^^^^^^^^^^^^^^

Collection Name
"""""""""""""""
Use ``'SENTINEL-3'`` as the collection name.

.. code-block:: python

   results = searcher.search(collection_name='SENTINEL-3')

Geographic Parameters
^^^^^^^^^^^^^^^^^^^^^

Geometry
""""""""
Region of Interest defined in Well Known Text (WKT) format with coordinates in decimal degrees (EPSG:4326).

.. code-block:: python

   # Polygon example
   aoi_wkt = 'POLYGON((0 35, 10 35, 10 45, 0 45, 0 35))'
   results = searcher.search(
       collection_name='SENTINEL-3',
       aoi_wkt=aoi_wkt
   )

Product Parameters
^^^^^^^^^^^^^^^^^^

Product Types
"""""""""""""
Sentinel-3 offers various product types organized by instrument. Product types use specific identifiers:

**Important Note:** While the configuration file lists generic categories (``S3OLCI``, ``S3SLSTR``, ``S3SRAL``, ``S3SRSP``), searches must use the specific product identifiers below for actual results.

**OLCI (Ocean and Land Colour Instrument):**

* ``OL_1_EFR___`` - Level 1 Earth Observation Full Resolution
* ``OL_1_ERR___`` - Level 1 Earth Observation Reduced Resolution  
* ``OL_2_LFR___`` - Level 2 Land Full Resolution
* ``OL_2_LRR___`` - Level 2 Land Reduced Resolution
* ``OL_2_WFR___`` - Level 2 Water Full Resolution
* ``OL_2_WRR___`` - Level 2 Water Reduced Resolution

**SLSTR (Sea and Land Surface Temperature Radiometer):**

* ``SL_1_RBT___`` - Level 1 Radiance and Brightness Temperature
* ``SL_2_LST___`` - Level 2 Land Surface Temperature
* ``SL_2_WST___`` - Level 2 Water Surface Temperature
* ``SL_2_FRP___`` - Level 2 Fire Radiative Power

**SRAL (SAR Radar Altimeter):**

* ``SR_1_SRA___`` - Level 1 Standard Radar Altimetry
* ``SR_1_SRA_A_`` - Level 1 Standard Radar Altimetry A
* ``SR_1_SRA_BS`` - Level 1 Standard Radar Altimetry BS
* ``SR_2_LAN___`` - Level 2 Land Altimetry
* ``SR_2_LAN_HY`` - Level 2 Land Altimetry (Hydrology)
* ``SR_2_LAN_LI`` - Level 2 Land Altimetry (Land Ice)
* ``SR_2_LAN_SI`` - Level 2 Land Altimetry (Sea Ice)
* ``SR_2_WAT___`` - Level 2 Water Altimetry

**SYNERGY Products:**

* ``SY_2_SYN___`` - Level 2 Synergy
* ``SY_2_V10___`` - Level 2 VGT 1km
* ``SY_2_VG1___`` - Level 2 VGT 1/3km
* ``SY_2_VGP___`` - Level 2 VGT Parameters
* ``SY_2_AOD___`` - Level 2 Aerosol Optical Depth

.. code-block:: python

   # Search for OLCI Level 2 water products
   results = searcher.search(
       collection_name='SENTINEL-3',
       product_type='OL_2_WFR___',
       attributes={'processingLevel': '2'}
   )

Processing Level
""""""""""""""""
Available processing levels:

* ``1`` - Level 1 (TOA radiances, brightness temperatures)
* ``2`` - Level 2 (Geophysical products)

.. code-block:: python

   # Search for Level 2 products
   results = searcher.search(
       collection_name='SENTINEL-3',
       attributes={'processingLevel': '2'}
   )

Platform Serial Identifier
""""""""""""""""""""""""""
Sentinel-3 constellation satellites:

* ``A`` - Sentinel-3A (launched 2016)
* ``B`` - Sentinel-3B (launched 2018)

.. code-block:: python

   # Search for Sentinel-3A data only
   results = searcher.search(
       collection_name='SENTINEL-3',
       attributes={'platformSerialIdentifier': 'A'}
   )

Instrument Short Name
"""""""""""""""""""""
Sentinel-3 instruments:

* ``OLCI`` - Ocean and Land Colour Instrument
* ``SLSTR`` - Sea and Land Surface Temperature Radiometer
* ``SRAL`` - SAR Radar Altimeter

.. code-block:: python

   # Search for OLCI instrument data
   results = searcher.search(
       collection_name='SENTINEL-3',
       attributes={'instrumentShortName': 'OLCI'}
   )

Cloud Cover
^^^^^^^^^^^

Cloud Cover Percentage
""""""""""""""""""""""
Filter products by cloud cover percentage (0-100%). Applicable mainly to OLCI and SLSTR products.

.. code-block:: python

   # Search for products with less than 30% cloud cover
   results = searcher.search(
       collection_name='SENTINEL-3',
       attributes={'cloudCover': '[0,30]'}
   )

Orbit Parameters
^^^^^^^^^^^^^^^^

Orbit Direction
"""""""""""""""
* ``ASCENDING`` - Satellite moving from south to north
* ``DESCENDING`` - Satellite moving from north to south

.. code-block:: python

   results = searcher.search(
       collection_name='SENTINEL-3',
       orbit_direction='DESCENDING'
   )

Orbit Number
""""""""""""
Absolute orbit number (integer value or range).

.. code-block:: python

   # Single orbit
   results = searcher.search(
       collection_name='SENTINEL-3',
       attributes={'orbitNumber': '12345'}
   )

   # Orbit range
   results = searcher.search(
       collection_name='SENTINEL-3',
       attributes={'orbitNumber': '[12345,12350]'}
   )

Relative Orbit Number
"""""""""""""""""""""
Relative orbit number (1-385 for Sentinel-3), representing the orbit within a repeat cycle.

.. code-block:: python

   # Search for relative orbit 100
   results = searcher.search(
       collection_name='SENTINEL-3',
       attributes={'relativeOrbitNumber': '100'}
   )

Quality and Timeliness
^^^^^^^^^^^^^^^^^^^^^^

Timeliness
""""""""""
Data delivery timeliness categories:

* ``NR`` - Near Real-Time
* ``NT`` - Non Time-Critical
* ``ST`` - Slow Time-Critical

.. code-block:: python

   # Search for non time-critical data
   results = searcher.search(
       collection_name='SENTINEL-3',
       attributes={'timeliness': 'NT'}
   )

Processing Baseline
"""""""""""""""""""
Processing baseline version (affects product quality and algorithms used).

.. code-block:: python

   # Search for specific processing baseline
   results = searcher.search(
       collection_name='SENTINEL-3',
       attributes={'processingBaseline': '03.00'}
   )

Additional Coverage Attributes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Sentinel-3 supports various coverage-related attributes for filtering products based on surface type percentages:

Coverage Types
""""""""""""""
* ``landCover`` - Percentage of land coverage
* ``cloudCover`` - Percentage of cloud coverage
* ``brightCover`` - Percentage of bright surface coverage
* ``coastalCover`` - Percentage of coastal area coverage
* ``closedSeaCover`` - Percentage of closed sea coverage
* ``openOceanCover`` - Percentage of open ocean coverage
* ``snowOrIceCover`` - Percentage of snow or ice coverage
* ``salineWaterCover`` - Percentage of saline water coverage
* ``tidalRegionCover`` - Percentage of tidal region coverage
* ``continentalIceCover`` - Percentage of continental ice coverage
* ``freshInlandWaterCover`` - Percentage of fresh inland water coverage

.. code-block:: python

   # Search for products with significant ocean coverage
   results = searcher.search(
       collection_name='SENTINEL-3',
       product_type='S3OLCI',
       attributes={
           'openOceanCover': '[60,100]',
           'cloudCover': '[0,20]'
       }
   )

Orbit Cycle Parameters
""""""""""""""""""""""
* ``cycleNumber`` - Orbit cycle number
* ``lastOrbitNumber`` - Last orbit number in product
* ``lastOrbitDirection`` - Last orbit direction (ASCENDING/DESCENDING)
* ``lastRelativeOrbitNumber`` - Last relative orbit number

.. code-block:: python

   # Search using cycle number
   results = searcher.search(
       collection_name='SENTINEL-3',
       attributes={'cycleNumber': '100'}
   )

Other Attributes
""""""""""""""""
* ``baselineCollection`` - Baseline collection identifier
* ``processorName`` - Name of the processor used
* ``processingCenter`` - Processing center identifier
* ``processorVersion`` - Version of the processor
* ``processingDate`` - Date of product processing

Practical Examples
------------------

Example 1: Ocean Color Monitoring
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from phidown import CopernicusDataSearcher

   searcher = CopernicusDataSearcher()
   
   # Search for OLCI ocean color products
   results = searcher.search(
       collection_name='SENTINEL-3',
       product_type='S3OLCI',
       aoi_wkt='POLYGON((0 35, 10 35, 10 45, 0 45, 0 35))',  # Mediterranean
       start_date='2023-06-01',
       end_date='2023-06-30',
       attributes={
           'instrumentShortName': 'OLCI',
           'processingLevel': 'L2',
           'cloudCover': '[0,20]',
           'openOceanCover': '[50,100]'
       }
   )
   
   print(f"Found {len(results)} ocean color products")

Example 2: Land Surface Temperature
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from phidown import CopernicusDataSearcher

   searcher = CopernicusDataSearcher()
   
   # Search for SLSTR land surface temperature products
   results = searcher.search(
       collection_name='SENTINEL-3',
       product_type='SL_2_LST___',
       aoi_wkt='POLYGON((10 40, 20 40, 20 50, 10 50, 10 40))',  # Central Europe
       start_date='2023-07-01',
       end_date='2023-07-31',
       attributes={
           'instrumentShortName': 'SLSTR',
           'processingLevel': '2',
           'timeliness': 'NT',
           'landCover': '[70,100]'
       }
   )
   
   print(f"Found {len(results)} land surface temperature products")

Example 3: Altimetry for Ocean Monitoring
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from phidown import CopernicusDataSearcher

   searcher = CopernicusDataSearcher()
   
   # Search for SRAL ocean altimetry products
   results = searcher.search(
       collection_name='SENTINEL-3',
       product_type='SR_2_WAT___',
       aoi_wkt='POLYGON((-10 30, 10 30, 10 50, -10 50, -10 30))',  # Atlantic
       start_date='2023-08-01',
       end_date='2023-08-31',
       attributes={
           'instrumentShortName': 'SRAL',
           'processingLevel': '2'
       }
   )
   
   print(f"Found {len(results)} ocean altimetry products")

Example 4: Synergy Products for Vegetation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from phidown import CopernicusDataSearcher

   searcher = CopernicusDataSearcher()
   
   # Search for SYNERGY vegetation products
   results = searcher.search(
       collection_name='SENTINEL-3',
       product_type='SY_2_VG1___',
       aoi_wkt='POLYGON((0 40, 20 40, 20 60, 0 60, 0 40))',  # Europe
       start_date='2023-05-01',
       end_date='2023-05-31',
       attributes={
           'processingLevel': '2',
           'cloudCover': '[0,30]'
       }
   )
   
   print(f"Found {len(results)} vegetation products")

Example 5: Fire Detection
^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from phidown import CopernicusDataSearcher

   searcher = CopernicusDataSearcher()
   
   # Search for SLSTR fire products
   results = searcher.search(
       collection_name='SENTINEL-3',
       product_type='SL_2_FRP___',
       aoi_wkt='POLYGON((-10 35, 5 35, 5 45, -10 45, -10 35))',  # Spain/Portugal
       start_date='2023-08-01',
       end_date='2023-08-31',
       attributes={
           'instrumentShortName': 'SLSTR',
           'processingLevel': '2',
           'timeliness': 'NR'
       }
   )
   
   print(f"Found {len(results)} fire detection products")

Example 6: Multi-Platform Time Series
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from phidown import CopernicusDataSearcher
   import pandas as pd

   searcher = CopernicusDataSearcher()
   
   # Search for data from both platforms
   s3a_results = searcher.search(
       collection_name='SENTINEL-3',
       product_type='OL_2_LFR___',
       aoi_wkt='POLYGON((10 45, 15 45, 15 50, 10 50, 10 45))',
       start_date='2023-01-01',
       end_date='2023-12-31',
       attributes={
           'platformSerialIdentifier': 'A',
           'processingLevel': '2',
           'cloudCover': '[0,30]'
       }
   )
   
   s3b_results = searcher.search(
       collection_name='SENTINEL-3',
       product_type='OL_2_LFR___',
       aoi_wkt='POLYGON((10 45, 15 45, 15 50, 10 50, 10 45))',
       start_date='2023-01-01',
       end_date='2023-12-31',
       attributes={
           'platformSerialIdentifier': 'B',
           'processingLevel': '2',
           'cloudCover': '[0,30]'
       }
   )
   
   # Combine results
   all_results = pd.concat([s3a_results, s3b_results], ignore_index=True)
   
   print(f"Sentinel-3A: {len(s3a_results)} products")
   print(f"Sentinel-3B: {len(s3b_results)} products")
   print(f"Total: {len(all_results)} products")

Search Optimization Tips
------------------------

1. **Choose Appropriate Instrument:** Select the right instrument for your application (OLCI for ocean color, SLSTR for temperature, SRAL for altimetry).

2. **Use Processing Level Wisely:** Level 1 for raw data processing, Level 2 for ready-to-use geophysical products.

3. **Filter by Cloud Cover:** For optical instruments (OLCI, SLSTR), use cloud cover filtering to get clear observations.

4. **Consider Timeliness:** Use Near Real-Time (NR) for urgent applications, Non Time-Critical (NT) for better quality.

5. **Optimize Temporal Range:** Use appropriate date ranges based on the 27-day repeat cycle.

6. **Use Relative Orbit Numbers:** For consistent geometry in time series analysis.

7. **Select Proper Product Type:** Choose full resolution (FR) for detailed analysis, reduced resolution (RR) for overview applications.

Common Use Cases
----------------

**Ocean Applications:**
- Ocean color monitoring: OL_2_WFR___, clear conditions
- Sea surface temperature: SL_2_WST___, thermal channels
- Ocean altimetry: SR_2_WAT___, precise measurements
- Marine ecosystem monitoring: OL_2_WFR___, regular coverage

**Land Applications:**
- Land surface temperature: SL_2_LST___, thermal infrared
- Vegetation monitoring: SY_2_VG1___, SYNERGY products
- Land altimetry: SR_2_LAN___, elevation measurements
- Fire detection: SL_2_FRP___, active fire monitoring

**Atmospheric Applications:**
- Aerosol monitoring: SY_2_AOD___, atmospheric products
- Cloud detection: All optical products with cloud masks
- Atmospheric correction: Level 2 products

**Ice Applications:**
- Sea ice monitoring: SR_2_LAN_SI, specialized altimetry
- Ice surface temperature: SL_2_LST___, polar regions
- Ice extent mapping: OLCI and SLSTR products

Technical Specifications
-------------------------

**OLCI (Ocean and Land Colour Instrument):**
- Spectral range: 400-1020 nm
- Spatial resolution: 300 m (FR), 1.2 km (RR)
- Swath width: 1270 km
- Spectral bands: 21 bands
- Applications: Ocean color, vegetation, atmosphere

**SLSTR (Sea and Land Surface Temperature Radiometer):**
- Spectral range: 0.55-12 μm
- Spatial resolution: 500 m (optical), 1 km (thermal)
- Swath width: 1400 km
- Spectral bands: 9 bands (6 optical, 3 thermal)
- Applications: Sea/land surface temperature, fire detection

**SRAL (SAR Radar Altimeter):**
- Frequency: 13.575 GHz (Ku-band), 5.41 GHz (C-band)
- Footprint: ~300 m (ocean), ~1.65 km (land/ice)
- Precision: ~3 cm (ocean), ~10 cm (land/ice)
- Applications: Ocean/land topography, ice thickness

**Orbital Characteristics:**
- Altitude: 814.5 km
- Inclination: 98.65°
- Repeat cycle: 27 days
- Revisit time: <1 day (depending on latitude)
- Local time: 10:00 AM (descending node)

**Coverage:**
- Global coverage: Daily
- Polar coverage: Multiple times per day
- Equatorial coverage: Every 2-3 days
- Ice-free ocean: Complete coverage every 27 days

For more detailed information about Sentinel-3 specifications and applications, refer to the official ESA Sentinel-3 documentation.
