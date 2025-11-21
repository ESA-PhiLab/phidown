.. Φ-Down documentation master file

Welcome to Φ-Down Documentation
===============================

**Φ-Down** is your simple gateway to Copernicus data - effortlessly search and download Earth Observation data from the Copernicus Data Space Ecosystem.

.. image:: ../../assets/logo.png
   :alt: Φ-Down Logo
   :align: center
   :width: 500px

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   getting_started
   installation
   cli
   user_guide
   ais_guide
   api_reference
   examples
   sentinel1_reference
   sentinel1_burst_mode
   sentinel2_reference
   sentinel3_reference
   landsat8_reference
   contributing
   changelog

Overview
--------

Φ-Down provides a Python interface to search and download Copernicus satellite data including:

- **Sentinel-1**: SAR data for land and ocean monitoring
- **Sentinel-2**: Multi-spectral imaging for land monitoring
- **Sentinel-3**: Ocean and land monitoring
- **Sentinel-5P**: Atmospheric monitoring
- **AIS Data**: Automatic Identification System data for maritime vessel tracking

Key Features
------------

* 🖥️ **Command-Line Interface**: Download products directly from terminal (NEW!)
* 🔍 **Search**: Query Copernicus Data Space using intuitive filters
* 📥 **Download**: Efficient data downloading with S3 integration
* 🗺️ **Visualization**: Built-in tools for plotting and interactive maps
* 🎯 **Interactive Tools**: Polygon selection tools for area of interest
* 📊 **Data Management**: Pandas integration for result handling
* 🚢 **AIS Data**: Access maritime vessel tracking data with temporal and spatial filtering

Quick Start
-----------

Install Φ-Down:

.. code-block:: bash

   pip install phidown

Search for data:

.. code-block:: python

   from phidown import CopernicusDataSearcher

   searcher = CopernicusDataSearcher()
   results = searcher.search(
       collection_name='SENTINEL-2',
       aoi_wkt='POLYGON((12.4 41.9, 12.5 41.9, 12.5 42.0, 12.4 42.0, 12.4 41.9))',
       start_date='2023-01-01',
       end_date='2023-01-31'
   )

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

