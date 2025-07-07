Sentinel-1 Reference Guide
==========================

This reference guide provides detailed information about Sentinel-1 SAR data parameters and options available through the Copernicus Data Space Ecosystem.

Overview
--------

Sentinel-1 is a constellation of two polar-orbiting satellites (Sentinel-1A and Sentinel-1B) carrying a C-band Synthetic Aperture Radar (SAR) instrument. The mission provides continuous all-weather, day-and-night imagery for land and ocean services.

**Key Features:**
- C-band SAR instrument operating at 5.405 GHz
- Four exclusive acquisition modes
- Dual polarization capability (HH+HV, VV+VH)
- 12-day repeat cycle (6 days with both satellites)
- Global coverage

Search Parameters
-----------------

**Parameter Types**

When searching for Sentinel-1 data, parameters are passed in two ways:

1. **Direct Parameters:** Passed directly to the ``search()`` method
   - ``collection_name`` - Mission/collection identifier
   - ``product_type`` - Product type (GRD, SLC, OCN, etc.)
   - ``orbit_direction`` - Orbit direction (ASCENDING/DESCENDING)
   - ``aoi_wkt`` - Area of interest in WKT format
   - ``start_date`` / ``end_date`` - Temporal range
   - ``top`` - Maximum number of results

2. **Attributes:** Passed in the ``attributes`` dictionary
   - ``sensorMode`` - Acquisition mode (IW, EW, SM, WV)
   - ``platform`` - Satellite platform (S1A, S1B)
   - ``polarisation`` - Polarization combination
   - ``processingLevel`` - Processing level
   - ``relativeOrbitNumber`` - Relative orbit number
   - ``orbitNumber`` - Absolute orbit number
   - ``instrument`` - Instrument type
   - ``status`` - Product availability status
   - ``timeliness`` - Data delivery timeliness
   - ``processingBaseline`` - Processing baseline version
   - ``swathIdentifier`` - Specific swath identifier

Basic Parameters
^^^^^^^^^^^^^^^^

Collection Name
"""""""""""""""
Use ``'SENTINEL-1'`` as the collection name.

.. code-block:: python

   results = searcher.search(collection_name='SENTINEL-1')

Geographic Parameters
^^^^^^^^^^^^^^^^^^^^^

Geometry
""""""""
Region of Interest defined in Well Known Text (WKT) format with coordinates in decimal degrees (EPSG:4326).

.. code-block:: python

   # Polygon example
   aoi_wkt = 'POLYGON((12.4 41.9, 12.5 41.9, 12.5 42.0, 12.4 42.0, 12.4 41.9))'
   results = searcher.search(
       collection_name='SENTINEL-1',
       aoi_wkt=aoi_wkt
   )


Product Parameters
^^^^^^^^^^^^^^^^^^

Product Types
"""""""""""""
Sentinel-1 offers various product types for different applications:

**Main Product Types:**

* ``GRD`` - Ground Range Detected (most common for applications)
* ``SLC`` - Single Look Complex (for interferometry)
* ``OCN`` - Ocean products
* ``RAW`` - Raw data

**Detailed Product Types:**

*Ground Range Detected (GRD):*
- ``GRD`` - Generic GRD
- ``GRD-COG`` - Cloud Optimized GeoTIFF format
- ``S1_GRDF_1S`` to ``S6_GRDF_1S`` - Full resolution GRD
- ``S1_GRDH_1S`` to ``S6_GRDH_1S`` - High resolution GRD
- ``S1_GRDM_1S`` to ``S6_GRDM_1S`` - Medium resolution GRD
- ``IW_GRDH_1S``, ``IW_GRDM_1S`` - Interferometric Wide swath
- ``EW_GRDH_1S``, ``EW_GRDM_1S`` - Extra Wide swath
- ``WV_GRDM_1S`` - Wave mode

*Single Look Complex (SLC):*
- ``SLC`` - Generic SLC
- ``S1_SLC__1S`` to ``S6_SLC__1S`` - Stripmap SLC
- ``IW_SLC__1S`` - Interferometric Wide swath SLC
- ``EW_SLC__1S`` - Extra Wide swath SLC
- ``WV_SLC__1S`` - Wave mode SLC

*Ocean Products:*
- ``OCN`` - Generic Ocean
- ``S1_OCN__2S`` to ``S6_OCN__2S`` - Stripmap Ocean
- ``IW_OCN__2S`` - Interferometric Wide swath Ocean
- ``EW_OCN__2S`` - Extra Wide swath Ocean
- ``WV_OCN__2S`` - Wave mode Ocean

*Raw Data:*
- ``RAW`` - Generic Raw
- ``S1_RAW__0S`` to ``S6_RAW__0S`` - Stripmap Raw
- ``IW_RAW__0S`` - Interferometric Wide swath Raw
- ``EW_RAW__0S`` - Extra Wide swath Raw

*Auxiliary Data:*
- ``AUX_PP1``, ``AUX_PP2`` - Processing Parameters
- ``AUX_CAL`` - Calibration data
- ``AUX_INS`` - Instrument data
- ``AUX_SCS`` - Satellite Control System data
- ``AUX_PREORB``, ``AUX_POEORB``, ``AUX_RESORB`` - Orbit data
- ``AUX_RESATT`` - Attitude data
- ``AUX_GNSSRD`` - GNSS raw data
- ``AUX_PROQUA`` - Product Quality data

.. code-block:: python

   # Search for GRD products
   results = searcher.search(
       collection_name='SENTINEL-1',
       product_type='GRD'
   )

Processing Level
""""""""""""""""
Available processing levels:

* ``LEVEL0`` - Raw data
* ``LEVEL1`` - Single Look Complex (SLC) and Ground Range Detected (GRD)
* ``LEVEL2`` - Ocean (OCN) and other derived products

.. code-block:: python

   # Search for LEVEL1 products
   results = searcher.search(
       collection_name='SENTINEL-1',
       attributes={'processingLevel': 'LEVEL1'}
   )

Platform
""""""""
Sentinel-1 constellation satellites:

* ``S1A`` - Sentinel-1A
* ``S1B`` - Sentinel-1B

.. code-block:: python

   # Search for Sentinel-1A data only
   results = searcher.search(
       collection_name='SENTINEL-1',
       attributes={'platform': 'S1A'}
   )

Swath Identifier
""""""""""""""""
Filter by specific swath. This is an attribute-based search.

* Stripmap (SM): ``S1`` to ``S6``
* Interferometric Wide (IW): ``IW1``, ``IW2``, ``IW3``
* Extra Wide (EW): ``EW1`` to ``EW5``
* Wave (WV): ``WV1``, ``WV2``

.. code-block:: python

   # Search for data from Stripmap swath S1
   results = searcher.search(
       collection_name='SENTINEL-1',
       attributes={'swathIdentifier': 'S1'}
   )

Instrument
""""""""""
* ``SAR`` - Synthetic Aperture Radar

.. code-block:: python

   # Search for SAR instrument data
   results = searcher.search(
       collection_name='SENTINEL-1',
       attributes={'instrument': 'SAR'}
   )

Sensor Mode
"""""""""""
Sentinel-1 acquisition modes:

* ``SM`` - Stripmap mode (S1-S6)
* ``IW`` - Interferometric Wide swath mode (default)
* ``EW`` - Extra-Wide swath mode
* ``WV`` - Wave mode

.. code-block:: python

   # Search for Interferometric Wide swath data
   results = searcher.search(
       collection_name='SENTINEL-1',
       attributes={'sensorMode': 'IW'}
   )

**Mode Characteristics:**

* **Stripmap (SM):** 80 km swath, 5 m resolution, 6 beams (S1-S6)
* **Interferometric Wide swath (IW):** 250 km swath, 5×20 m resolution, 3 sub-swaths
* **Extra Wide swath (EW):** 400 km swath, 20×40 m resolution, 5 sub-swaths
* **Wave (WV):** 20×20 km vignettes, 5 m resolution, for ocean applications

Orbit Parameters
^^^^^^^^^^^^^^^^

Orbit Direction
"""""""""""""""
* ``ASCENDING`` - Satellite moving from south to north
* ``DESCENDING`` - Satellite moving from north to south

.. code-block:: python

   results = searcher.search(
       collection_name='SENTINEL-1',
       orbit_direction='DESCENDING'
   )

Orbit Number
""""""""""""
Absolute orbit number (integer value or range).

.. code-block:: python

   # Single orbit
   results = searcher.search(
       collection_name='SENTINEL-1',
       attributes={'orbitNumber': 12345}
   )

Relative Orbit Number
"""""""""""""""""""""
Relative orbit number (1-175 for Sentinel-1), representing the orbit within a repeat cycle.

.. code-block:: python

   # Search for relative orbit 87
   results = searcher.search(
       collection_name='SENTINEL-1',
       attributes={'relativeOrbitNumber': 87}
   )

Polarization
^^^^^^^^^^^^

Sentinel-1 supports various polarization combinations:

* ``HH`` - Horizontal transmit, Horizontal receive
* ``VV`` - Vertical transmit, Vertical receive
* ``HH%26VH`` - Horizontal transmit, Horizontal and Vertical receive
* ``VV%26VH`` - Vertical transmit, Vertical and Horizontal receive
* ``VH%26VV`` - Vertical transmit, Horizontal and Vertical receive
* ``VH%26HH`` - Vertical transmit, Horizontal and Vertical receive
* ``HH%26HV`` - Horizontal transmit, Horizontal and Vertical receive
* ``VV%26HV`` - Vertical transmit, Vertical and Horizontal receive
* ``HV%26HH`` - Horizontal transmit, Vertical and Horizontal receive
* ``HV%26VV`` - Horizontal transmit, Vertical and Vertical receive

.. code-block:: python

   # Search for dual polarization VV+VH
   results = searcher.search(
       collection_name='SENTINEL-1',
       attributes={'polarisation': 'VV%26VH'}
   )

**Polarization by Mode:**
- **IW and EW modes:** VV+VH or HH+HV
- **SM mode:** Single (HH, VV, HV, VH) or dual polarization
- **WV mode:** Single polarization (HH or VV)

Quality and Timeliness
^^^^^^^^^^^^^^^^^^^^^^

Timeliness
""""""""""
Data delivery timeliness categories:

* ``NRT-10m`` - Near Real-Time within 10 minutes
* ``NRT-3h`` - Near Real-Time within 3 hours
* ``Fast-24h`` - Fast delivery within 24 hours
* ``Off-line`` - Standard offline processing
* ``Reprocessing`` - Reprocessed data

.. code-block:: python

   # Search for near real-time data
   results = searcher.search(
       collection_name='SENTINEL-1',
       attributes={'timeliness': 'NRT-3h'}
   )

Processing Baseline
"""""""""""""""""""
Processing baseline version (affects product quality and algorithms used).

.. code-block:: python

   # Search for specific processing baseline
   results = searcher.search(
       collection_name='SENTINEL-1',
       attributes={'processingBaseline': '003.40'}
   )

Status
""""""
Product availability status:

* ``ONLINE`` - Immediately available for download
* ``OFFLINE`` - Requires retrieval from long-term storage
* ``ALL`` - Both online and offline products

.. code-block:: python

   # Search for immediately available products
   results = searcher.search(
       collection_name='SENTINEL-1',
       attributes={'status': 'ONLINE'}
   )
   results = searcher.search(
       collection_name='SENTINEL-1',
       status='ONLINE'
   )

Practical Examples
------------------

Example 1: Basic IW GRD Search
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from phidown import CopernicusDataSearcher

   searcher = CopernicusDataSearcher()
   
   # Search for standard IW GRD products
   results = searcher.search(
       collection_name='SENTINEL-1',
       product_type='GRD',
       aoi_wkt='POLYGON((12.4 41.9, 12.5 41.9, 12.5 42.0, 12.4 42.0, 12.4 41.9))',
       start_date='2023-06-01',
       end_date='2023-06-30',
       orbit_direction='DESCENDING',
       attributes={'sensorMode': 'IW'}
   )
   
   print(f"Found {len(results)} IW GRD products")

Example 2: Interferometric SLC Search
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from phidown import CopernicusDataSearcher

   searcher = CopernicusDataSearcher()
   
   # Search for SLC products suitable for interferometry
   results = searcher.search(
       collection_name='SENTINEL-1',
       product_type='SLC',
       aoi_wkt='POLYGON((12.4 41.9, 12.5 41.9, 12.5 42.0, 12.4 42.0, 12.4 41.9))',
       start_date='2023-06-01',
       end_date='2023-06-30',
       orbit_direction='DESCENDING',
       attributes={
           'sensorMode': 'IW',
           'polarisation': 'VV%26VH',
           'relativeOrbitNumber': 87
       }
   )
   
   print(f"Found {len(results)} SLC products for interferometry")

Example 3: Ocean Applications
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from phidown import CopernicusDataSearcher

   searcher = CopernicusDataSearcher()
   
   # Search for ocean products and wave mode data
   ocean_results = searcher.search(
       collection_name='SENTINEL-1',
       product_type='OCN',
       aoi_wkt='POLYGON((0 35, 10 35, 10 45, 0 45, 0 35))',  # Mediterranean
       start_date='2023-06-01',
       end_date='2023-06-30'
   )
   
   wave_results = searcher.search(
       collection_name='SENTINEL-1',
       product_type='GRD',
       aoi_wkt='POLYGON((0 35, 10 35, 10 45, 0 45, 0 35))',
       start_date='2023-06-01',
       end_date='2023-06-30',
       attributes={'sensorMode': 'WV'}
   )
   
   print(f"Found {len(ocean_results)} ocean products and {len(wave_results)} wave mode products")

Example 4: Time Series Analysis
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from phidown import CopernicusDataSearcher
   import pandas as pd

   searcher = CopernicusDataSearcher()
   
   # Search for consistent time series data
   results = searcher.search(
       collection_name='SENTINEL-1',
       product_type='GRD',
       aoi_wkt='POLYGON((12.4 41.9, 12.5 41.9, 12.5 42.0, 12.4 42.0, 12.4 41.9))',
       start_date='2023-01-01',
       end_date='2023-12-31',
       orbit_direction='DESCENDING',
       attributes={
           'sensorMode': 'IW',
           'relativeOrbitNumber': 87,
           'polarisation': 'VV%26VH'
       }
   )
   
   # Group by date to analyze temporal coverage
   results['Date'] = pd.to_datetime(results['ContentDate']).dt.date
   temporal_coverage = results.groupby('Date').size()
   
   print(f"Found {len(results)} products over {len(temporal_coverage)} unique dates")

Example 5: Multi-Platform Search
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from phidown import CopernicusDataSearcher

   searcher = CopernicusDataSearcher()
   
   # Compare data from both Sentinel-1A and Sentinel-1B
   s1a_results = searcher.search(
       collection_name='SENTINEL-1',
       product_type='GRD',
       aoi_wkt='POLYGON((12.4 41.9, 12.5 41.9, 12.5 42.0, 12.4 42.0, 12.4 41.9))',
       start_date='2023-06-01',
       end_date='2023-06-30',
       attributes={'platform': 'S1A'}
   )
   
   s1b_results = searcher.search(
       collection_name='SENTINEL-1',
       product_type='GRD',
       aoi_wkt='POLYGON((12.4 41.9, 12.5 41.9, 12.5 42.0, 12.4 42.0, 12.4 41.9))',
       start_date='2023-06-01',
       end_date='2023-06-30',
       attributes={'platform': 'S1B'}
   )
   
   print(f"Sentinel-1A: {len(s1a_results)} products")
   print(f"Sentinel-1B: {len(s1b_results)} products")

Search Optimization Tips
------------------------

1. **Use Relative Orbit Numbers:** For time series analysis, filter by relative orbit number to ensure consistent geometry.

2. **Specify Orbit Direction:** Choose ascending or descending based on your application needs.

3. **Filter by Polarization:** Select appropriate polarization for your analysis (VV+VH for most land applications).

4. **Consider Processing Baseline:** Newer baselines generally provide better quality but may not be available for historical data.

5. **Use Sensor Mode Appropriately:**
   - IW for most land applications (use ``attributes={'sensorMode': 'IW'}``)
   - EW for wide-area monitoring (use ``attributes={'sensorMode': 'EW'}``)
   - WV for ocean wave analysis (use ``attributes={'sensorMode': 'WV'}``)

6. **Check Product Status:** Use ``attributes={'status': 'ONLINE'}`` for immediate download needs.

Common Use Cases
----------------

**Land Applications:**
- Deforestation monitoring: IW GRD, VV+VH polarization
- Urban change detection: IW GRD, VV polarization
- Agricultural monitoring: IW GRD, VV+VH polarization

**Ocean Applications:**
- Ship detection: IW GRD, VV polarization
- Oil spill monitoring: IW GRD, VV polarization
- Wave analysis: WV mode products

**Interferometry:**
- Ground deformation: IW SLC, same relative orbit
- Topographic mapping: IW SLC, interferometric pairs

**Emergency Response:**
- Flood mapping: IW GRD, VV polarization
- Disaster assessment: IW GRD, available polarization

Technical Specifications
-------------------------

**Frequency:** 5.405 GHz (C-band)
**Repeat Cycle:** 12 days (constellation), 6 days (with both satellites)
**Orbital Altitude:** 693 km
**Incidence Angle Range:** 20-47 degrees
**Swath Width:** 
- SM: 80 km
- IW: 250 km
- EW: 400 km
- WV: 20 km

**Spatial Resolution:**
- SM: 5 m (single-look)
- IW: 5×20 m (single-look)
- EW: 20×40 m (single-look)
- WV: 5 m (single-look)

For more detailed information about Sentinel-1 specifications and applications, refer to the official ESA Sentinel-1 documentation.
