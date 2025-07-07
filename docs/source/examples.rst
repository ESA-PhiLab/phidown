Examples
========

This section provides practical examples of using Φ-Down for common Earth Observation tasks.

Example 1: Basic Sentinel-2 Search
----------------------------------

Search for Sentinel-2 data over a specific area:

.. code-block:: python

   from phidown import CopernicusDataSearcher

   # Initialize searcher
   searcher = CopernicusDataSearcher()
   
   # Define area of interest (Rome, Italy)
   rome_wkt = 'POLYGON((12.4 41.9, 12.5 41.9, 12.5 42.0, 12.4 42.0, 12.4 41.9))'
   
   # Search for data
   results = searcher.search(
       collection_name='SENTINEL-2',
       aoi_wkt=rome_wkt,
       start_date='2023-06-01',
       end_date='2023-06-30',
       cloud_cover_threshold=20
   )
   
   # Display results
   print(f"Found {len(results)} products")
   searcher.display_results(results, columns=['Name', 'ContentDate', 'CloudCover'])

Example 2: Sentinel-1 SAR Data Search
-------------------------------------

Search for Sentinel-1 SAR data with specific parameters:

.. code-block:: python

   from phidown import CopernicusDataSearcher

   searcher = CopernicusDataSearcher()
   
   # Define area of interest (Netherlands)
   netherlands_wkt = 'POLYGON((3.4 50.8, 7.2 50.8, 7.2 53.6, 3.4 53.6, 3.4 50.8))'
   
   # Search for Sentinel-1 GRD products
   results = searcher.search(
       collection_name='SENTINEL-1',
       product_type='GRD',
       aoi_wkt=netherlands_wkt,
       start_date='2023-05-01',
       end_date='2023-05-31',
       orbit_direction='DESCENDING'
   )
   
   print(f"Found {len(results)} SAR products")
   for idx, row in results.iterrows():
       print(f"Product: {row['Name']}")
       print(f"Date: {row['ContentDate']}")
       print(f"Orbit: {row['OrbitDirection']}")
       print("---")

Example 3: Multi-Mission Search
-----------------------------------

Search across multiple missions for comprehensive coverage:

.. code-block:: python

   from phidown import CopernicusDataSearcher
   import pandas as pd

   searcher = CopernicusDataSearcher()
   
   # Define area of interest (Mediterranean Sea)
   mediterranean_wkt = 'POLYGON((0 30, 30 30, 30 45, 0 45, 0 30))'
   
   # Search multiple missions
   missions = ['SENTINEL-1', 'SENTINEL-2', 'SENTINEL-3']
   all_results = []
   
   for mission in missions:
       print(f"Searching {mission}...")
       results = searcher.search(
           collection_name=mission,
           aoi_wkt=mediterranean_wkt,
           start_date='2023-07-01',
           end_date='2023-07-07'
       )
       results['Mission'] = mission
       all_results.append(results)
   
   # Combine results
   combined_results = pd.concat(all_results, ignore_index=True)
   print(f"Total products found: {len(combined_results)}")
   
   # Group by mission
   mission_counts = combined_results.groupby('Mission').size()
   print("Products per mission:")
   for mission, count in mission_counts.items():
       print(f"  {mission}: {count}")

Example 4: Download with Progress Tracking
------------------------------------------

Download products with progress monitoring:

.. code-block:: python

   from phidown import CopernicusDataSearcher
   from phidown.downloader import pull_down
   import os
   from tqdm import tqdm

   # Search for products
   searcher = CopernicusDataSearcher()
   results = searcher.search(
       collection_name='SENTINEL-2',
       aoi_wkt='POLYGON((12.4 41.9, 12.5 41.9, 12.5 42.0, 12.4 42.0, 12.4 41.9))',
       start_date='2023-06-01',
       end_date='2023-06-30',
       cloud_cover_threshold=10
   )
   
   # Create download directory
   download_dir = './sentinel2_data'
   os.makedirs(download_dir, exist_ok=True)
   
   # Download products with progress bar
   for idx, row in tqdm(results.iterrows(), total=len(results), desc="Downloading"):
       product_id = row['Id']
       product_name = row['Name']
       
       print(f"Downloading: {product_name}")
       try:
           pull_down(product_id, download_dir=download_dir)
           print(f"✓ Downloaded: {product_name}")
       except Exception as e:
           print(f"✗ Failed: {product_name} - {e}")

Example 5: Interactive Polygon Selection
----------------------------------------

Use interactive tools to select area of interest:

.. code-block:: python

   from phidown import create_polygon_tool, search_with_polygon
   
   # Create interactive polygon tool
   tool = create_polygon_tool(
       center=[45.0, 9.0],  # Milan, Italy
       zoom=8
   )
   
   # Display the tool (in Jupyter notebook)
   tool.display()
   
   # After drawing polygon, get WKT
   # wkt = tool.get_wkt()
   # print(f"Selected area: {wkt}")
   
   # Or use the integrated search function
   # results = search_with_polygon(
   #     collection_name='SENTINEL-2',
   #     start_date='2023-06-01',
   #     end_date='2023-06-30'
   # )

Example 6: Time Series Analysis
-----------------------------------

Analyze temporal patterns in search results:

.. code-block:: python

   from phidown import CopernicusDataSearcher
   import pandas as pd
   import matplotlib.pyplot as plt

   searcher = CopernicusDataSearcher()
   
   # Search for one year of data
   results = searcher.search(
       collection_name='SENTINEL-2',
       aoi_wkt='POLYGON((12.4 41.9, 12.5 41.9, 12.5 42.0, 12.4 42.0, 12.4 41.9))',
       start_date='2023-01-01',
       end_date='2023-12-31',
       cloud_cover_threshold=30
   )
   
   # Convert ContentDate to datetime
   results['Date'] = pd.to_datetime(results['ContentDate'])
   
   # Group by month
   monthly_counts = results.groupby(results['Date'].dt.to_period('M')).size()
   monthly_cloud_cover = results.groupby(results['Date'].dt.to_period('M'))['CloudCover'].mean()
   
   # Plot results
   fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
   
   # Product count per month
   monthly_counts.plot(kind='bar', ax=ax1)
   ax1.set_title('Sentinel-2 Products per Month')
   ax1.set_ylabel('Number of Products')
   
   # Average cloud cover per month
   monthly_cloud_cover.plot(kind='line', ax=ax2, marker='o')
   ax2.set_title('Average Cloud Cover per Month')
   ax2.set_ylabel('Cloud Cover (%)')
   
   plt.tight_layout()
   plt.show()

Example 7: Batch Processing with Error Handling
-----------------------------------------------

Process multiple areas with robust error handling:

.. code-block:: python

   from phidown import CopernicusDataSearcher
   from phidown.downloader import pull_down
   import time
   import logging

   # Set up logging
   logging.basicConfig(level=logging.INFO)
   logger = logging.getLogger(__name__)

   # Define multiple areas of interest
   areas = {
       'Rome': 'POLYGON((12.4 41.9, 12.5 41.9, 12.5 42.0, 12.4 42.0, 12.4 41.9))',
       'Milan': 'POLYGON((9.1 45.4, 9.2 45.4, 9.2 45.5, 9.1 45.5, 9.1 45.4))',
       'Naples': 'POLYGON((14.2 40.8, 14.3 40.8, 14.3 40.9, 14.2 40.9, 14.2 40.8))'
   }
   
   searcher = CopernicusDataSearcher()
   
   for area_name, wkt in areas.items():
       logger.info(f"Processing {area_name}...")
       
       try:
           # Search for data
           results = searcher.search(
               collection_name='SENTINEL-2',
               aoi_wkt=wkt,
               start_date='2023-06-01',
               end_date='2023-06-30',
               cloud_cover_threshold=15
           )
           
           logger.info(f"Found {len(results)} products for {area_name}")
           
           # Download first product if available
           if len(results) > 0:
               best_product = results.loc[results['CloudCover'].idxmin()]
               product_id = best_product['Id']
               
               logger.info(f"Downloading best product: {best_product['Name']}")
               pull_down(product_id, download_dir=f'./data/{area_name}')
               logger.info(f"✓ Downloaded product for {area_name}")
           else:
               logger.warning(f"No products found for {area_name}")
               
       except Exception as e:
           logger.error(f"Error processing {area_name}: {e}")
           continue
           
       # Be respectful to the API
       time.sleep(2)

Example 8: Advanced Filtering and Analysis
------------------------------------------

Apply complex filters and analyze results:

.. code-block:: python

   from phidown import CopernicusDataSearcher
   import pandas as pd
   import numpy as np

   searcher = CopernicusDataSearcher()
   
   # Search for data
   results = searcher.search(
       collection_name='SENTINEL-2',
       aoi_wkt='POLYGON((12.4 41.9, 12.5 41.9, 12.5 42.0, 12.4 42.0, 12.4 41.9))',
       start_date='2023-01-01',
       end_date='2023-12-31'
   )
   
   # Advanced filtering
   # Filter for high-quality images
   high_quality = results[
       (results['CloudCover'] < 10) & 
       (results['ProductType'] == 'L2A')
   ]
   
   # Group by season
   results['Date'] = pd.to_datetime(results['ContentDate'])
   results['Season'] = results['Date'].dt.month.map({
       12: 'Winter', 1: 'Winter', 2: 'Winter',
       3: 'Spring', 4: 'Spring', 5: 'Spring',
       6: 'Summer', 7: 'Summer', 8: 'Summer',
       9: 'Autumn', 10: 'Autumn', 11: 'Autumn'
   })
   
   # Analyze by season
   seasonal_analysis = results.groupby('Season').agg({
       'CloudCover': ['mean', 'std', 'count'],
       'Size': 'mean'
   }).round(2)
   
   print("Seasonal Analysis:")
   print(seasonal_analysis)
   
   # Find the best acquisition per month
   best_monthly = results.loc[results.groupby(results['Date'].dt.to_period('M'))['CloudCover'].idxmin()]
   
   print("\nBest acquisition per month:")
   for idx, row in best_monthly.iterrows():
       print(f"{row['Date'].strftime('%Y-%m')}: {row['Name']} (Cloud Cover: {row['CloudCover']}%)")

Example 9: Visualization and Mapping
------------------------------------

Create visualizations of search results:

.. code-block:: python

   from phidown import CopernicusDataSearcher, plot_kml_coordinates
   import folium
   from shapely.geometry import Point
   from shapely.wkt import loads

   searcher = CopernicusDataSearcher()
   
   # Search for data
   results = searcher.search(
       collection_name='SENTINEL-2',
       aoi_wkt='POLYGON((12.4 41.9, 12.5 41.9, 12.5 42.0, 12.4 42.0, 12.4 41.9))',
       start_date='2023-06-01',
       end_date='2023-06-30',
       cloud_cover_threshold=20
   )
   
   # Use built-in plotting function
   plot_kml_coordinates(results)
   
   # Create custom map
   center_lat, center_lon = 41.95, 12.45
   m = folium.Map(location=[center_lat, center_lon], zoom_start=10)
   
   # Add search area
   search_area = loads('POLYGON((12.4 41.9, 12.5 41.9, 12.5 42.0, 12.4 42.0, 12.4 41.9))')
   folium.GeoJson(
       search_area.__geo_interface__,
       style_function=lambda x: {'color': 'red', 'weight': 2, 'fillOpacity': 0.1}
   ).add_to(m)
   
   # Add product footprints (if available in results)
   for idx, row in results.iterrows():
       if 'Footprint' in row and row['Footprint']:
           folium.GeoJson(
               loads(row['Footprint']).__geo_interface__,
               popup=f"Product: {row['Name']}<br>Date: {row['ContentDate']}<br>Cloud Cover: {row['CloudCover']}%",
               style_function=lambda x: {'color': 'blue', 'weight': 1, 'fillOpacity': 0.3}
           ).add_to(m)
   
   # Save map
   m.save('search_results_map.html')
   print("Map saved as 'search_results_map.html'")

Example 10: Configuration and Customization
-------------------------------------------

Customize search parameters and configuration:

.. code-block:: python

   from phidown import CopernicusDataSearcher
   import json

   # Load custom configuration
   custom_config = {
       "SENTINEL-2": {
           "product_types": ["L1C", "L2A"],
           "attributes": {
               "processingLevel": "L2A",
               "cloudCover": "[0 TO 20]"
           }
       }
   }
   
   searcher = CopernicusDataSearcher()
   searcher.config = custom_config
   
   # Search with custom attributes
   results = searcher.search(
       collection_name='SENTINEL-2',
       aoi_wkt='POLYGON((12.4 41.9, 12.5 41.9, 12.5 42.0, 12.4 42.0, 12.4 41.9))',
       start_date='2023-06-01',
       end_date='2023-06-30',
       attributes={'processingLevel': 'L2A'}
   )
   
   # Save configuration
   with open('custom_config.json', 'w') as f:
       json.dump(custom_config, f, indent=2)
   
   print(f"Found {len(results)} products with custom configuration")

Tips for Using Examples
-----------------------

1. **Modify coordinates**: Replace the example coordinates with your area of interest
2. **Adjust date ranges**: Use appropriate date ranges for your analysis
3. **Handle credentials**: Ensure your ``secret.yml`` file is properly configured
4. **Monitor API limits**: Be respectful of API rate limits when processing large datasets
5. **Error handling**: Always include proper error handling in production code
6. **Data storage**: Organize downloaded data in a structured manner

For more examples and use cases, check the `notebooks/` directory in the repository.
