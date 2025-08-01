Landsat-8 Reference Guide
=========================

This reference guide provides detailed information about Landsat-8 data parameters and options available through the Copernicus Data Space Ecosystem.

Overview
--------

Landsat-8 is an Earth observation satellite launched in 2013, carrying two primary instruments for systematic land monitoring. The mission continues the Landsat program's legacy of providing consistent, high-quality multispectral imagery for land use, land cover change detection, and environmental monitoring.

**Key Features:**
- Operational Land Imager (OLI) - 9 spectral bands including coastal/aerosol band
- Thermal Infrared Sensor (TIRS) - 2 thermal infrared bands
- 16-day repeat cycle with global coverage
- 30-meter spatial resolution for multispectral bands
- 100-meter spatial resolution for thermal bands
- 15-meter panchromatic band for image sharpening

Search Parameters
-----------------

**Parameter Types**

When searching for Landsat-8 data, parameters are passed in two ways:

1. **Direct Parameters:** Passed directly to the ``search()`` method
   - ``collection_name`` - Mission/collection identifier
   - ``product_type`` - Product type (L1GT, L1T, L1TP, L2SP)
   - ``aoi_wkt`` - Area of interest in WKT format
   - ``start_date`` / ``end_date`` - Temporal range
   - ``top`` - Maximum number of results

2. **Attributes:** Passed in the ``attributes`` dictionary
   - ``processingLevel`` - Processing level (LEVEL1, LEVEL2, etc.)
   - ``platform`` - Satellite platform (LANDSAT-8)
   - ``instrument`` - Instrument type (OLI_TIRS)
   - ``orbitNumber`` - Absolute orbit number
   - ``sensorMode`` - Sensor mode (DEFAULT)
   - ``cloudCover`` - Cloud cover percentage
   - ``status`` - Product availability status
   - ``organisationName`` - Data provider (ESA, USGS)
   - ``path`` - WRS-2 path number
   - ``row`` - WRS-2 row number
   - ``sunAzimuth`` - Sun azimuth angle
   - ``sunElevation`` - Sun elevation angle

Basic Parameters
^^^^^^^^^^^^^^^^

Collection Name
"""""""""""""""
Use ``'LANDSAT-8-ESA'`` as the collection name.

.. code-block:: python

   results = searcher.search(collection_name='LANDSAT-8-ESA')

Geographic Parameters
^^^^^^^^^^^^^^^^^^^^^

Geometry
""""""""
Region of Interest defined in Well Known Text (WKT) format with coordinates in decimal degrees (EPSG:4326).

.. code-block:: python

   # Polygon example
   aoi_wkt = 'POLYGON((-120 35, -110 35, -110 45, -120 45, -120 35))'
   results = searcher.search(
       collection_name='LANDSAT-8-ESA',
       aoi_wkt=aoi_wkt
   )

Product Parameters
^^^^^^^^^^^^^^^^^^

Product Types
"""""""""""""
Landsat-8 offers various product types with different processing levels:

.. table:: Landsat-8 Product Types
    :widths: 15 65 20
    :header-rows: 1

    * - Level
      - Description
      - Identifier
    * - **Level 1**
      - **Systematic Terrain Correction:** Radiometrically calibrated and geometrically corrected using GLS2000 DEM
      - ``L1GT``
    * - **Level 1**
      - **Precision Terrain Correction:** Systematic terrain correction with improved accuracy using DEM
      - ``L1T``
    * - **Level 1**
      - **Precision and Terrain Correction:** Highest geometric accuracy using ground control points and DEM
      - ``L1TP``
    * - **Level 2**
      - **Surface Reflectance:** Atmospherically corrected surface reflectance with quality assessment
      - ``L2SP``

.. code-block:: python

   # Search for Level 2 surface reflectance products
   results = searcher.search(
       collection_name='LANDSAT-8-ESA',
       product_type='L2SP'
   )

Processing Level
""""""""""""""""
Available processing levels:

* ``LEVEL1`` / ``LEVEL1GT`` - Level 1 Systematic Terrain Correction
* ``LEVEL1T`` - Level 1 Precision Terrain Correction  
* ``LEVEL1TP`` - Level 1 Precision and Terrain Correction
* ``LEVEL2`` / ``LEVEL2SP`` - Level 2 Surface Reflectance

.. code-block:: python

   # Search for Level 2 products
   results = searcher.search(
       collection_name='LANDSAT-8-ESA',
       attributes={'processingLevel': 'LEVEL2'}
   )

Platform
""""""""
Landsat-8 platform:

* ``LANDSAT-8`` - Landsat-8 satellite (launched 2013)

.. code-block:: python

   # Search for Landsat-8 data
   results = searcher.search(
       collection_name='LANDSAT-8-ESA',
       attributes={'platform': 'LANDSAT-8'}
   )

Instrument
""""""""""
Landsat-8 instrument:

* ``OLI_TIRS`` - Combined Operational Land Imager and Thermal Infrared Sensor

.. code-block:: python

   # Search for OLI/TIRS data
   results = searcher.search(
       collection_name='LANDSAT-8-ESA',
       attributes={'instrument': 'OLI_TIRS'}
   )

Sensor Mode
"""""""""""
Landsat-8 sensor mode:

* ``DEFAULT`` - Standard Earth observation mode

.. code-block:: python

   # Search for default sensor mode
   results = searcher.search(
       collection_name='LANDSAT-8-ESA',
       attributes={'sensorMode': 'DEFAULT'}
   )

Cloud Cover
^^^^^^^^^^^

Cloud Cover Percentage
""""""""""""""""""""""
Filter products by cloud cover percentage (0-100%).

.. code-block:: python

   # Search for products with less than 20% cloud cover
   results = searcher.search(
       collection_name='LANDSAT-8-ESA',
       attributes={'cloudCover': '[0,20]'}
   )

WRS-2 Path/Row Parameters
^^^^^^^^^^^^^^^^^^^^^^^^^

Path and Row
""""""""""""
Landsat-8 uses the Worldwide Reference System-2 (WRS-2) for systematic coverage:

* ``path`` - WRS-2 path number (1-233)
* ``row`` - WRS-2 row number (1-248)

.. code-block:: python

   # Search for specific path/row
   results = searcher.search(
       collection_name='LANDSAT-8-ESA',
       attributes={
           'path': '44',
           'row': '34'
       }
   )

Orbit Parameters
^^^^^^^^^^^^^^^^

Orbit Number
""""""""""""
Absolute orbit number (integer value or range).

.. code-block:: python

   # Single orbit
   results = searcher.search(
       collection_name='LANDSAT-8-ESA',
       attributes={'orbitNumber': '12345'}
   )

   # Orbit range
   results = searcher.search(
       collection_name='LANDSAT-8-ESA',
       attributes={'orbitNumber': '[12345,12350]'}
   )

Solar Angle Parameters
^^^^^^^^^^^^^^^^^^^^^^

Sun Azimuth and Elevation
"""""""""""""""""""""""""
Solar illumination conditions during image acquisition:

* ``sunAzimuth`` - Sun azimuth angle in degrees
* ``sunElevation`` - Sun elevation angle in degrees

.. code-block:: python

   # Search for optimal solar conditions
   results = searcher.search(
       collection_name='LANDSAT-8-ESA',
       attributes={
           'sunElevation': '[30,90]',  # High sun elevation
           'sunAzimuth': '[120,240]'   # Southern illumination
       }
   )

Data Provider
^^^^^^^^^^^^^

Organisation Name
"""""""""""""""""
Data provider organizations:

* ``ESA`` - European Space Agency
* ``USGS`` - United States Geological Survey

.. code-block:: python

   # Search for USGS-provided data
   results = searcher.search(
       collection_name='LANDSAT-8-ESA',
       attributes={'organisationName': 'USGS'}
   )

Quality and Status
^^^^^^^^^^^^^^^^^^

Status
""""""
Product availability status:

* ``ONLINE`` - Immediately available for download
* ``OFFLINE`` - Requires retrieval from long-term storage
* ``ALL`` - Both online and offline products

.. code-block:: python

   # Search for immediately available products
   results = searcher.search(
       collection_name='LANDSAT-8-ESA',
       attributes={'status': 'ONLINE'}
   )

Practical Examples
------------------

Example 1: Agricultural Monitoring
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from phidown import CopernicusDataSearcher

   searcher = CopernicusDataSearcher()
   
   # Search for surface reflectance products over agricultural area
   results = searcher.search(
       collection_name='LANDSAT-8-ESA',
       product_type='L2SP',
       aoi_wkt='POLYGON((-100 40, -95 40, -95 45, -100 45, -100 40))',  # Midwest US
       start_date='2023-06-01',
       end_date='2023-08-31',
       attributes={
           'cloudCover': '[0,10]',
           'sunElevation': '[45,90]'
       }
   )
   
   print(f'Found {len(results)} agricultural monitoring products')

Example 2: Urban Heat Island Analysis
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from phidown import CopernicusDataSearcher

   searcher = CopernicusDataSearcher()
   
   # Search for thermal infrared data for urban analysis
   results = searcher.search(
       collection_name='LANDSAT-8-ESA',
       product_type='L2SP',
       aoi_wkt='POLYGON((-74.25 40.5, -73.7 40.5, -73.7 40.9, -74.25 40.9, -74.25 40.5))',  # NYC
       start_date='2023-07-01',
       end_date='2023-07-31',
       attributes={
           'cloudCover': '[0,15]',
           'instrument': 'OLI_TIRS'
       }
   )
   
   print(f'Found {len(results)} urban thermal products')

Example 3: Forest Change Detection
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from phidown import CopernicusDataSearcher

   searcher = CopernicusDataSearcher()
   
   # Search for specific path/row for consistent geometry
   results = searcher.search(
       collection_name='LANDSAT-8-ESA',
       product_type='L2SP',
       start_date='2020-01-01',
       end_date='2023-12-31',
       attributes={
           'path': '226',
           'row': '62',  # Amazon region
           'cloudCover': '[0,20]',
           'processingLevel': 'LEVEL2'
       }
   )
   
   print(f'Found {len(results)} forest monitoring products')

Example 4: Coastal Water Quality
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from phidown import CopernicusDataSearcher

   searcher = CopernicusDataSearcher()
   
   # Search for coastal aerosol band data
   results = searcher.search(
       collection_name='LANDSAT-8-ESA',
       product_type='L2SP',
       aoi_wkt='POLYGON((-81 24, -80 24, -80 26, -81 26, -81 24))',  # Florida Keys
       start_date='2023-01-01',
       end_date='2023-12-31',
       attributes={
           'cloudCover': '[0,5]',
           'bands': '3'  # Coastal/aerosol band
       }
   )
   
   print(f'Found {len(results)} coastal water quality products')

Example 5: Seasonal Vegetation Analysis
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from phidown import CopernicusDataSearcher
   import pandas as pd

   searcher = CopernicusDataSearcher()
   
   # Search for multi-seasonal data
   seasons = [
       ('Spring', '2023-03-01', '2023-05-31'),
       ('Summer', '2023-06-01', '2023-08-31'),
       ('Fall', '2023-09-01', '2023-11-30')
   ]
   
   all_results = []
   for season_name, start_date, end_date in seasons:
       results = searcher.search(
           collection_name='LANDSAT-8-ESA',
           product_type='L2SP',
           aoi_wkt='POLYGON((-106 39, -105 39, -105 40, -106 40, -106 39))',  # Colorado
           start_date=start_date,
           end_date=end_date,
           attributes={
               'cloudCover': '[0,15]',
               'path': '33',
               'row': '32'
           }
       )
       results['season'] = season_name
       all_results.append(results)
   
   combined_results = pd.concat(all_results, ignore_index=True)
   print(f'Found {len(combined_results)} seasonal products')

Example 6: Solar Angle Optimization
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from phidown import CopernicusDataSearcher

   searcher = CopernicusDataSearcher()
   
   # Search for optimal solar illumination conditions
   results = searcher.search(
       collection_name='LANDSAT-8-ESA',
       product_type='L1TP',
       aoi_wkt='POLYGON((-110 35, -105 35, -105 40, -110 40, -110 35))',  # Utah
       start_date='2023-05-01',
       end_date='2023-09-30',
       attributes={
           'cloudCover': '[0,10]',
           'sunElevation': '[50,90]',  # High sun angle
           'sunAzimuth': '[150,210]'   # Southern aspect
       }
   )
   
   print(f'Found {len(results)} optimally illuminated products')

Search Optimization Tips
------------------------

1. **Use Appropriate Processing Level:** L1TP for geometric accuracy, L2SP for atmospheric correction.

2. **Filter by Cloud Cover:** Essential for optical analysis - use strict thresholds for quantitative work.

3. **Consider Solar Angles:** High sun elevation reduces shadows, specific azimuth angles optimize illumination.

4. **Use Path/Row for Consistency:** Same path/row ensures consistent viewing geometry for time series.

5. **Optimize Temporal Windows:** Account for 16-day repeat cycle and seasonal variations.

6. **Select Proper Bands:** Use coastal/aerosol band for atmospheric studies, thermal bands for temperature.

7. **Consider Data Provider:** USGS typically provides the most complete archive.

Common Use Cases
----------------

**Land Cover Mapping:**
- Surface reflectance products: L2SP with low cloud cover
- Multi-seasonal data for phenology
- Consistent path/row for change detection

**Agricultural Applications:**
- NDVI/vegetation indices: Bands 4 (red) and 5 (NIR)
- Crop stress monitoring: Thermal bands 10 and 11
- Irrigation mapping: SWIR bands 6 and 7

**Water Quality Monitoring:**
- Coastal/aerosol band: Band 1 for atmospheric correction
- Turbidity assessment: Visible bands 2, 3, 4
- Algal bloom detection: Red edge simulation

**Urban Studies:**
- Urban heat islands: Thermal bands with high spatial detail
- Impervious surface mapping: SWIR and thermal combinations
- Air quality: Coastal/aerosol band

**Forest Monitoring:**
- Deforestation detection: Multi-temporal L2SP products
- Fire mapping: Thermal anomalies in bands 10 and 11
- Health assessment: Red edge proxy using NIR/red ratio

**Geological Applications:**
- Mineral mapping: SWIR bands 6 and 7
- Rock type discrimination: Band combinations
- Structural geology: Panchromatic band for detail

Technical Specifications
-------------------------

**OLI (Operational Land Imager):**
- Spectral range: 0.43-1.38 μm
- Spatial resolution: 30 m (multispectral), 15 m (panchromatic)
- Swath width: 185 km
- Spectral bands: 9 bands including coastal/aerosol
- Radiometric resolution: 12-bit

**TIRS (Thermal Infrared Sensor):**
- Spectral range: 10.6-12.51 μm  
- Spatial resolution: 100 m (resampled to 30 m)
- Swath width: 185 km
- Spectral bands: 2 thermal infrared bands
- Radiometric resolution: 12-bit

**Orbital Characteristics:**
- Altitude: 705 km
- Inclination: 98.2°
- Repeat cycle: 16 days
- Revisit time: 16 days
- Local time: 10:00 AM (descending node)
- WRS-2 system: 233 paths × 248 rows

**Spectral Bands:**

.. table:: Landsat-8 Spectral Bands
    :widths: 10 25 20 20 25
    :header-rows: 1

    * - Band
      - Name
      - Wavelength (μm)
      - Resolution (m)
      - Primary Use
    * - 1
      - Coastal/Aerosol
      - 0.43-0.45
      - 30
      - Coastal studies, aerosol
    * - 2
      - Blue
      - 0.45-0.51
      - 30
      - Water, atmosphere
    * - 3
      - Green
      - 0.53-0.59
      - 30
      - Vegetation, water
    * - 4
      - Red
      - 0.64-0.67
      - 30
      - Vegetation, soils
    * - 5
      - NIR
      - 0.85-0.88
      - 30
      - Vegetation, water
    * - 6
      - SWIR-1
      - 1.57-1.65
      - 30
      - Moisture, minerals
    * - 7
      - SWIR-2
      - 2.11-2.29
      - 30
      - Geology, minerals
    * - 8
      - Panchromatic
      - 0.50-0.68
      - 15
      - Image sharpening
    * - 9
      - Cirrus
      - 1.36-1.38
      - 30
      - Cloud detection
    * - 10
      - TIRS-1
      - 10.60-11.19
      - 100
      - Surface temperature
    * - 11
      - TIRS-2
      - 11.50-12.51
      - 100
      - Surface temperature

**Coverage:**
- Global land coverage: Every 16 days
- Scene size: 185 × 185 km
- Daily imaging capacity: ~400 scenes
- Archive: February 2013 to present

For more detailed information about Landsat-8 specifications and data processing, refer to the official USGS Landsat documentation.
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
