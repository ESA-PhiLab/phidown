# Data Retrieval Guide

This comprehensive guide covers advanced techniques for searching, filtering, and downloading SAR data efficiently using the SAR Project APIs.

## Search Strategies

### Temporal Filtering

#### Basic Date Ranges
```python
from sar_project import SARClient
from datetime import datetime, timedelta

client = SARClient(api_key='your_api_key')

# Last 30 days
end_date = datetime.now()
start_date = end_date - timedelta(days=30)

products = client.search(
    start_date=start_date.strftime('%Y-%m-%d'),
    end_date=end_date.strftime('%Y-%m-%d'),
    product_type='SLC'
)
```

#### Seasonal Analysis
```python
# Get all winter data for multiple years
winter_products = []

for year in range(2020, 2024):
    # December - February
    winter_start = f"{year}-12-01"
    winter_end = f"{year+1}-02-28"
    
    products = client.search(
        start_date=winter_start,
        end_date=winter_end,
        product_type='SLC',
        instrument_mode='IW'
    )
    winter_products.extend(products)

print(f"Found {len(winter_products)} winter acquisitions")
```

#### Regular Time Series
```python
# Monthly acquisitions for time series
def get_monthly_products(year, bbox, max_per_month=5):
    monthly_data = {}
    
    for month in range(1, 13):
        start_date = f"{year}-{month:02d}-01"
        if month == 12:
            end_date = f"{year+1}-01-01"
        else:
            end_date = f"{year}-{month+1:02d}-01"
        
        products = client.search(
            start_date=start_date,
            end_date=end_date,
            bbox=bbox,
            product_type='SLC',
            max_results=max_per_month
        )
        monthly_data[month] = products
    
    return monthly_data

# Get data for Mediterranean region
bbox = [0, 30, 20, 45]  # Mediterranean
monthly_2023 = get_monthly_products(2023, bbox)
```

### Spatial Filtering

#### Bounding Box Searches
```python
# Different regions of interest
regions = {
    'mediterranean': [0, 30, 20, 45],
    'north_sea': [-5, 50, 10, 60],
    'baltic_sea': [10, 53, 30, 66],
    'black_sea': [27, 40, 42, 48]
}

region_data = {}
for region_name, bbox in regions.items():
    products = client.search(
        start_date='2023-01-01',
        end_date='2023-12-31',
        bbox=bbox,
        product_type='SLC'
    )
    region_data[region_name] = products
    print(f"{region_name}: {len(products)} products")
```

#### Point-based Searches with Buffer
```python
# Search around specific locations
locations = {
    'gibraltar': [-5.35, 36.14],
    'suez_canal': [32.35, 30.52],
    'bosphorus': [29.02, 41.12]
}

for location_name, coords in locations.items():
    products = client.search(
        start_date='2023-01-01',
        end_date='2023-12-31',
        point=coords,
        buffer_km=100,  # 100km radius
        product_type='SLC'
    )
    print(f"{location_name}: {len(products)} products within 100km")
```

#### Complex Geometry Searches
```python
from shapely.geometry import Polygon
import json

# Define complex area of interest
coastline_polygon = Polygon([
    [-10, 35], [5, 35], [8, 38], [10, 42], 
    [8, 45], [3, 47], [-2, 45], [-8, 40], [-10, 35]
])

# Search using GeoJSON
products = client.search(
    start_date='2023-01-01',
    end_date='2023-12-31',
    geometry=coastline_polygon.__geo_interface__,
    product_type='SLC'
)

print(f"Found {len(products)} products intersecting coastline")
```

### Product Filtering

#### Multi-criteria Filtering
```python
# Complex search with multiple criteria
search_criteria = {
    'temporal': {
        'start_date': '2023-06-01',
        'end_date': '2023-08-31'
    },
    'spatial': {
        'bbox': [10, 40, 20, 50]
    },
    'product': {
        'product_type': 'SLC',
        'platform': 'S1A',
        'instrument_mode': 'IW',
        'polarization': 'VV'
    },
    'quality': {
        'data_quality': 'GOOD',
        'cloud_coverage': {'max': 10}
    },
    'technical': {
        'orbit_direction': 'ASCENDING',
        'relative_orbit': {'min': 100, 'max': 200}
    }
}

products = client.search(**search_criteria)
```

#### Custom Filtering Functions
```python
def filter_by_custom_criteria(products):
    """Apply custom filtering logic"""
    filtered = []
    
    for product in products:
        # Custom quality criteria
        if (product.size_mb > 500 and 
            product.orbit_number % 10 == 0 and  # Every 10th orbit
            'ASCENDING' in product.pass_direction):
            filtered.append(product)
    
    return filtered

# Apply custom filter
all_products = client.search(
    start_date='2023-01-01',
    end_date='2023-12-31',
    product_type='SLC'
)

custom_filtered = filter_by_custom_criteria(all_products)
print(f"Custom filter: {len(custom_filtered)}/{len(all_products)} products")
```

## Advanced Search Techniques

### Orbit-based Searches
```python
# Search by specific orbit characteristics
def get_orbit_products(relative_orbit, cycle_range=None):
    """Get products for specific relative orbit"""
    search_params = {
        'start_date': '2023-01-01',
        'end_date': '2023-12-31',
        'relative_orbit': relative_orbit,
        'product_type': 'SLC'
    }
    
    if cycle_range:
        search_params['cycle_number'] = cycle_range
    
    return client.search(**search_params)

# Get data for specific orbital tracks
orbit_87_products = get_orbit_products(87)
orbit_160_products = get_orbit_products(160, {'min': 300, 'max': 320})
```

### Interferometric Pair Discovery
```python
def find_interferometric_pairs(bbox, max_temporal_baseline=24):
    """Find suitable interferometric pairs"""
    # Get all products in area
    products = client.search(
        start_date='2023-01-01',
        end_date='2023-12-31',
        bbox=bbox,
        product_type='SLC',
        instrument_mode='IW'
    )
    
    pairs = []
    for i, product1 in enumerate(products):
        for product2 in products[i+1:]:
            # Same relative orbit
            if product1.relative_orbit != product2.relative_orbit:
                continue
            
            # Temporal baseline check
            date1 = datetime.fromisoformat(product1.sensing_date.replace('Z', ''))
            date2 = datetime.fromisoformat(product2.sensing_date.replace('Z', ''))
            temporal_baseline = abs((date2 - date1).days)
            
            if temporal_baseline <= max_temporal_baseline:
                pairs.append({
                    'master': product1,
                    'slave': product2,
                    'temporal_baseline_days': temporal_baseline,
                    'relative_orbit': product1.relative_orbit
                })
    
    return pairs

# Find interferometric pairs
study_area = [10, 40, 15, 45]
pairs = find_interferometric_pairs(study_area, max_temporal_baseline=12)
print(f"Found {len(pairs)} interferometric pairs")
```

### Multi-mission Searches
```python
# Search across multiple Sentinel-1 platforms
def multi_platform_search(search_params):
    """Search across S1A and S1B platforms"""
    all_products = []
    
    for platform in ['S1A', 'S1B']:
        platform_params = search_params.copy()
        platform_params['platform'] = platform
        
        products = client.search(**platform_params)
        all_products.extend(products)
    
    # Sort by sensing time
    all_products.sort(key=lambda x: x.sensing_date)
    return all_products

# Multi-platform search
multi_products = multi_platform_search({
    'start_date': '2023-01-01',
    'end_date': '2023-01-31',
    'bbox': [0, 35, 10, 45],
    'product_type': 'SLC'
})
```

## Download Strategies

### Selective Downloads
```python
# Download strategy based on data needs
def selective_download_strategy(products, analysis_type):
    """Choose download format based on analysis needs"""
    
    strategies = {
        'quick_survey': 'preview',
        'metadata_analysis': 'metadata', 
        'full_processing': 'full'
    }
    
    download_format = strategies.get(analysis_type, 'metadata')
    
    for product in products:
        result = client.download(
            product_id=product.id,
            output_dir=f'./data/{analysis_type}/',
            format=download_format
        )
        print(f"Downloaded {product.id} as {download_format}")

# Apply different strategies
quick_products = products[:5]
selective_download_strategy(quick_products, 'metadata_analysis')
```

### Priority-based Downloads
```python
def prioritized_download(products, priority_func):
    """Download products based on priority function"""
    
    # Add priority scores
    for product in products:
        product.priority = priority_func(product)
    
    # Sort by priority (highest first)
    products.sort(key=lambda x: x.priority, reverse=True)
    
    # Download high priority first
    for product in products:
        if product.priority > 0.7:  # High priority threshold
            client.download(
                product_id=product.id,
                output_dir='./priority_data/',
                format='full'
            )

def calculate_priority(product):
    """Calculate download priority based on various factors"""
    priority = 0.0
    
    # Recent data gets higher priority
    days_old = (datetime.now() - 
                datetime.fromisoformat(product.sensing_date.replace('Z', ''))).days
    priority += max(0, (30 - days_old) / 30) * 0.3
    
    # Quality factor
    if hasattr(product, 'data_quality'):
        quality_scores = {'EXCELLENT': 1.0, 'GOOD': 0.8, 'FAIR': 0.5, 'POOR': 0.2}
        priority += quality_scores.get(product.data_quality, 0.5) * 0.4
    
    # Size factor (prefer reasonable sizes)
    if 500 <= product.size_mb <= 2000:
        priority += 0.3
    
    return priority

# Apply prioritized download
prioritized_download(products, calculate_priority)
```

### Batch Download Management
```python
import concurrent.futures
import time

class BatchDownloadManager:
    def __init__(self, client, max_workers=3, max_size_gb=50):
        self.client = client
        self.max_workers = max_workers
        self.max_size_gb = max_size_gb
        self.downloaded_size = 0
        
    def download_with_limits(self, products):
        """Download with size and concurrency limits"""
        
        def download_single(product):
            if self.downloaded_size + (product.size_mb / 1024) > self.max_size_gb:
                return None, "Size limit reached"
            
            try:
                result = self.client.download(
                    product_id=product.id,
                    output_dir='./batch_downloads/',
                    format='metadata'
                )
                self.downloaded_size += product.size_mb / 1024
                return result, "Success"
            except Exception as e:
                return None, str(e)
        
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_product = {
                executor.submit(download_single, product): product 
                for product in products
            }
            
            for future in concurrent.futures.as_completed(future_to_product):
                product = future_to_product[future]
                result, status = future.result()
                results.append({
                    'product_id': product.id,
                    'result': result,
                    'status': status
                })
                
                if "Size limit reached" in status:
                    # Cancel remaining downloads
                    for remaining_future in future_to_product:
                        remaining_future.cancel()
                    break
        
        return results

# Use batch download manager
manager = BatchDownloadManager(client, max_workers=3, max_size_gb=10)
batch_results = manager.download_with_limits(products)

# Report results
successful = [r for r in batch_results if r['status'] == 'Success']
print(f"Successfully downloaded: {len(successful)} products")
```

## Data Organization

### Hierarchical Organization
```python
import os
from pathlib import Path

def organize_downloads(products, base_dir='./organized_data/'):
    """Organize downloads in hierarchical structure"""
    
    for product in products:
        # Extract date and platform info
        sensing_date = product.sensing_date[:10]  # YYYY-MM-DD
        year = sensing_date[:4]
        month = sensing_date[5:7]
        
        # Create directory structure
        org_dir = Path(base_dir) / product.platform / year / month
        org_dir.mkdir(parents=True, exist_ok=True)
        
        # Download to organized location
        result = client.download(
            product_id=product.id,
            output_dir=str(org_dir),
            format='metadata'
        )
        
        print(f"Organized: {result.filepath}")

# Apply organization
organize_downloads(products[:10])
```

### Metadata Database Creation
```python
import sqlite3
import json

def create_metadata_database(products, db_path='sar_metadata.db'):
    """Create SQLite database with product metadata"""
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            product_id TEXT PRIMARY KEY,
            platform TEXT,
            instrument_mode TEXT,
            product_type TEXT,
            sensing_date TEXT,
            orbit_number INTEGER,
            relative_orbit INTEGER,
            size_mb REAL,
            geometry TEXT,
            metadata_json TEXT,
            download_path TEXT
        )
    ''')
    
    # Insert product data
    for product in products:
        # Download and parse metadata
        result = client.download(
            product_id=product.id,
            output_dir='./temp_metadata/',
            format='metadata'
        )
        
        metadata = parser.parse_metadata(result.filepath)
        
        cursor.execute('''
            INSERT OR REPLACE INTO products VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            product.id,
            product.platform,
            product.instrument_mode,
            product.product_type,
            product.sensing_date,
            product.orbit_number,
            product.relative_orbit,
            product.size_mb,
            product.footprint,
            json.dumps(metadata.__dict__, default=str),
            result.filepath
        ))
    
    conn.commit()
    conn.close()
    print(f"Created database with {len(products)} products")

# Create metadata database
create_metadata_database(products)
```

## Performance Optimization

### Caching Strategies
```python
# Enable intelligent caching
client = SARClient(
    api_key='your_api_key',
    cache_enabled=True,
    cache_dir='./search_cache/',
    cache_ttl=3600  # 1 hour cache
)

# Cache search results for repeated queries
def cached_search(search_params, cache_key=None):
    """Search with custom caching"""
    if not cache_key:
        cache_key = hash(str(sorted(search_params.items())))
    
    cache_file = f"./search_cache/search_{cache_key}.json"
    
    # Check cache
    if os.path.exists(cache_file):
        with open(cache_file, 'r') as f:
            cached_results = json.load(f)
        print("Using cached results")
        return cached_results
    
    # Perform search
    results = client.search(**search_params)
    
    # Save to cache
    os.makedirs('./search_cache/', exist_ok=True)
    with open(cache_file, 'w') as f:
        json.dump([r.__dict__ for r in results], f, default=str)
    
    return results
```

### Parallel Processing
```python
import multiprocessing as mp
from functools import partial

def parallel_region_search(regions, search_params):
    """Search multiple regions in parallel"""
    
    def search_region(region_info, base_params):
        region_name, bbox = region_info
        params = base_params.copy()
        params['bbox'] = bbox
        
        try:
            products = client.search(**params)
            return region_name, products
        except Exception as e:
            return region_name, []
    
    # Prepare region list
    region_items = list(regions.items())
    
    # Use partial to fix base_params
    search_func = partial(search_region, base_params=search_params)
    
    # Parallel execution
    with mp.Pool(processes=min(len(region_items), 4)) as pool:
        results = pool.map(search_func, region_items)
    
    return dict(results)

# Search multiple regions in parallel
regions = {
    'region_1': [0, 30, 10, 40],
    'region_2': [10, 30, 20, 40],
    'region_3': [20, 30, 30, 40],
    'region_4': [30, 30, 40, 40]
}

base_search = {
    'start_date': '2023-01-01',
    'end_date': '2023-12-31',
    'product_type': 'SLC'
}

parallel_results = parallel_region_search(regions, base_search)
```

## Quality Control

### Data Validation
```python
def validate_downloaded_data(download_results):
    """Validate downloaded data integrity"""
    
    validation_results = []
    
    for result in download_results:
        validation = {
            'product_id': result.product_id,
            'file_exists': os.path.exists(result.filepath),
            'size_match': False,
            'checksum_valid': False,
            'metadata_parseable': False
        }
        
        if validation['file_exists']:
            # Check file size
            actual_size = os.path.getsize(result.filepath)
            expected_size = result.expected_size_bytes
            validation['size_match'] = abs(actual_size - expected_size) < 1024
            
            # Validate checksum if available
            if hasattr(result, 'checksum'):
                import hashlib
                with open(result.filepath, 'rb') as f:
                    file_hash = hashlib.md5(f.read()).hexdigest()
                validation['checksum_valid'] = file_hash == result.checksum
            
            # Try parsing metadata
            try:
                metadata = parser.parse_metadata(result.filepath)
                validation['metadata_parseable'] = True
            except:
                validation['metadata_parseable'] = False
        
        validation_results.append(validation)
    
    return validation_results

# Validate downloads
validation_report = validate_downloaded_data(download_results)
valid_count = sum(1 for v in validation_report if all(v.values()))
print(f"Valid downloads: {valid_count}/{len(validation_report)}")
```

### Coverage Analysis
```python
def analyze_coverage(products, target_region):
    """Analyze spatial and temporal coverage"""
    
    from shapely.geometry import box, Polygon
    from shapely.ops import unary_union
    
    # Target region as polygon
    if isinstance(target_region, list):
        target_poly = box(*target_region)
    else:
        target_poly = Polygon(target_region)
    
    # Collect product footprints
    product_polygons = []
    dates = []
    
    for product in products:
        # Parse footprint
        coords = eval(product.footprint.replace('POLYGON((', '[').replace('))', ']'))
        poly = Polygon(coords)
        product_polygons.append(poly)
        dates.append(product.sensing_date)
    
    # Calculate coverage
    total_coverage = unary_union(product_polygons)
    covered_area = target_poly.intersection(total_coverage).area
    total_area = target_poly.area
    coverage_percent = (covered_area / total_area) * 100
    
    # Temporal analysis
    dates.sort()
    temporal_span = (datetime.fromisoformat(dates[-1].replace('Z', '')) - 
                    datetime.fromisoformat(dates[0].replace('Z', ''))).days
    
    return {
        'spatial_coverage_percent': coverage_percent,
        'temporal_span_days': temporal_span,
        'product_count': len(products),
        'average_products_per_month': len(products) / (temporal_span / 30.44)
    }

# Analyze coverage
target_area = [5, 35, 15, 45]  # Study region
coverage_stats = analyze_coverage(products, target_area)
print(f"Coverage: {coverage_stats['spatial_coverage_percent']:.1f}%")
print(f"Temporal span: {coverage_stats['temporal_span_days']} days")
```

## Related Documentation
- [Getting Started Guide](getting-started.md)
- [Attribute Analysis](attribute-analysis.md)
- [Processing Workflows](processing-workflows.md)
- [Search API Reference](../api/search-api.md)
- [Download API Reference](../api/download-api.md)
