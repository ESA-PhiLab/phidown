# Getting Started with SAR Project

This guide provides step-by-step instructions to help you get started with the SAR (Synthetic Aperture Radar) project, from initial setup to your first data download and analysis.

## Prerequisites

### System Requirements
- **Python**: 3.8 or higher
- **Memory**: 8GB RAM minimum, 16GB recommended
- **Storage**: 100GB+ for product data
- **Network**: Stable internet connection for downloads

### Required Knowledge
- Basic Python programming
- Understanding of satellite data concepts
- Familiarity with geospatial data (helpful)

## Installation

### 1. Install SAR Project Package
```bash
# Install from PyPI
pip install sar-project

# Or install from source
git clone https://github.com/your-org/sar-project.git
cd sar-project
pip install -e .
```

### 2. Install Dependencies
```bash
# Required dependencies
pip install requests pandas numpy matplotlib

# Optional dependencies for advanced features
pip install geopandas rasterio shapely jupyter
```

### 3. Verify Installation
```python
import sar_project
print(sar_project.__version__)
```

## Authentication

### 1. Get API Credentials
1. Visit the [SAR Project Portal](https://portal.sar-project.org)
2. Create an account or sign in
3. Navigate to "API Access" section
4. Generate your API key

### 2. Configure Authentication
```python
from sar_project import SARClient

# Method 1: Direct API key
client = SARClient(api_key='your_api_key_here')

# Method 2: Environment variable
import os
os.environ['SAR_API_KEY'] = 'your_api_key_here'
client = SARClient()

# Method 3: Configuration file
client = SARClient.from_config('~/.sar_config.json')
```

### 3. Test Authentication
```python
# Test your credentials
try:
    status = client.test_connection()
    print("Authentication successful!")
except Exception as e:
    print(f"Authentication failed: {e}")
```

## First Steps

### 1. Search for Products
```python
from sar_project import SARClient
from datetime import datetime, timedelta

client = SARClient(api_key='your_api_key')

# Define search parameters
end_date = datetime.now()
start_date = end_date - timedelta(days=30)

# Search for recent products
products = client.search(
    start_date=start_date.strftime('%Y-%m-%d'),
    end_date=end_date.strftime('%Y-%m-%d'),
    product_type='SLC',
    platform='S1A',
    max_results=10
)

print(f"Found {len(products)} products")
for product in products[:5]:
    print(f"- {product.id}")
    print(f"  Date: {product.sensing_date}")
    print(f"  Size: {product.size_mb:.1f} MB")
```

### 2. Download Your First Product
```python
# Select a product to download
if products:
    product = products[0]
    print(f"Downloading: {product.id}")
    
    # Download metadata first (faster)
    result = client.download(
        product_id=product.id,
        output_dir='./downloads/',
        format='metadata'
    )
    
    print(f"Downloaded to: {result.filepath}")
```

### 3. Parse Product Metadata
```python
from sar_project import SARParser

parser = SARParser(api_key='your_api_key')

# Parse the downloaded metadata
metadata = parser.parse_metadata(
    file_path=result.filepath,
    extract_all=True
)

# Display key information
print("\n=== Product Information ===")
print(f"Platform: {metadata.basic_info.platform}")
print(f"Mode: {metadata.basic_info.instrument_mode}")
print(f"Product Type: {metadata.basic_info.product_type}")
print(f"Sensing Time: {metadata.temporal.sensing_start}")
print(f"Orbit: {metadata.orbital.orbit_number}")
print(f"Polarization: {metadata.technical.polarization}")
```

## Common Use Cases

### Case 1: Regional Monitoring
```python
# Search for products over a specific region
bbox = [-10, 35, 5, 45]  # [west, south, east, north]

regional_products = client.search(
    start_date='2023-01-01',
    end_date='2023-12-31',
    bbox=bbox,
    product_type='SLC',
    instrument_mode='IW'
)

print(f"Found {len(regional_products)} products over region")

# Download recent products
for product in regional_products[:3]:
    client.download(
        product_id=product.id,
        output_dir='./regional_data/',
        format='full'
    )
```

### Case 2: Time Series Analysis
```python
# Get time series for specific location
from datetime import datetime, timedelta

location = [2.5, 40.0]  # [longitude, latitude]
buffer_km = 50

# Search monthly for past year
time_series = []
current_date = datetime(2023, 1, 1)

while current_date < datetime(2024, 1, 1):
    end_date = current_date + timedelta(days=30)
    
    products = client.search(
        start_date=current_date.strftime('%Y-%m-%d'),
        end_date=end_date.strftime('%Y-%m-%d'),
        point=location,
        buffer_km=buffer_km,
        product_type='SLC'
    )
    
    time_series.extend(products)
    current_date = end_date

print(f"Time series contains {len(time_series)} products")
```

### Case 3: Quality Assessment
```python
# Analyze product quality metrics
quality_stats = []

for product in products[:10]:
    # Parse metadata
    metadata = parser.parse_metadata_from_id(product.id)
    
    quality_info = {
        'product_id': product.id,
        'platform': metadata.basic_info.platform,
        'quality': metadata.quality.data_quality,
        'noise_level': metadata.quality.noise_equivalent_sigma0,
        'phase_quality': metadata.quality.phase_quality
    }
    quality_stats.append(quality_info)

# Convert to DataFrame for analysis
import pandas as pd
df = pd.DataFrame(quality_stats)
print(df.groupby('quality').size())
```

## Data Visualization

### Basic Visualization
```python
import matplotlib.pyplot as plt
import pandas as pd

# Create product summary DataFrame
product_data = []
for product in products:
    product_data.append({
        'date': product.sensing_date,
        'platform': product.platform,
        'size_mb': product.size_mb,
        'orbit': product.orbit_number
    })

df = pd.DataFrame(product_data)
df['date'] = pd.to_datetime(df['date'])

# Plot acquisition timeline
plt.figure(figsize=(12, 6))
for platform in df['platform'].unique():
    platform_data = df[df['platform'] == platform]
    plt.scatter(platform_data['date'], platform_data['size_mb'], 
                label=platform, alpha=0.7)

plt.xlabel('Acquisition Date')
plt.ylabel('Product Size (MB)')
plt.title('SAR Product Acquisitions Over Time')
plt.legend()
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()
```

### Geographic Visualization
```python
# Visualize product coverage (requires geopandas)
try:
    import geopandas as gpd
    from shapely.geometry import Point
    
    # Extract geographic data
    geo_data = []
    for product in products:
        if hasattr(product, 'center_coordinates'):
            geo_data.append({
                'product_id': product.id,
                'geometry': Point(product.center_coordinates),
                'platform': product.platform,
                'date': product.sensing_date
            })
    
    # Create GeoDataFrame
    gdf = gpd.GeoDataFrame(geo_data)
    
    # Simple plot
    gdf.plot(column='platform', legend=True, figsize=(10, 8))
    plt.title('SAR Product Geographic Coverage')
    plt.show()
    
except ImportError:
    print("Install geopandas for geographic visualization")
```

## Configuration

### Configuration File
Create `~/.sar_config.json`:
```json
{
    "api_key": "your_api_key_here",
    "base_url": "https://api.sar-project.org/v1/",
    "download_dir": "./sar_data/",
    "cache_enabled": true,
    "cache_dir": "./sar_cache/",
    "max_concurrent_downloads": 3,
    "default_format": "metadata",
    "timeout_seconds": 300
}
```

### Environment Variables
```bash
# Add to your .bashrc or .zshrc
export SAR_API_KEY="your_api_key_here"
export SAR_DOWNLOAD_DIR="./sar_data/"
export SAR_CACHE_DIR="./sar_cache/"
```

## Best Practices

### 1. Data Management
```python
# Organize downloads by date and platform
def organized_download(product):
    date_str = product.sensing_date[:10]  # YYYY-MM-DD
    output_dir = f"./data/{product.platform}/{date_str}/"
    
    return client.download(
        product_id=product.id,
        output_dir=output_dir,
        format='metadata'
    )
```

### 2. Error Handling
```python
import time
from sar_project.exceptions import RateLimitExceeded, NetworkError

def robust_search(search_params, max_retries=3):
    """Search with automatic retry on failures"""
    for attempt in range(max_retries):
        try:
            return client.search(**search_params)
        except RateLimitExceeded as e:
            print(f"Rate limited, waiting {e.retry_after}s...")
            time.sleep(e.retry_after)
        except NetworkError as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                print(f"Network error, retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise e
    
    return []
```

### 3. Performance Optimization
```python
# Use batch operations when possible
product_ids = [p.id for p in products[:10]]

# Batch download
batch_result = client.download_batch(
    product_ids=product_ids,
    output_dir='./downloads/',
    format='metadata'
)

# Monitor batch progress
while not batch_result.is_complete():
    print(f"Progress: {batch_result.progress_percent}%")
    time.sleep(10)
```

## Troubleshooting

### Common Issues

#### 1. Authentication Errors
```python
# Check API key validity
try:
    client.test_connection()
except AuthenticationError:
    print("Invalid API key - check your credentials")
```

#### 2. Download Failures
```python
# Check available disk space
import shutil
free_space_gb = shutil.disk_usage('.').free / (1024**3)
print(f"Free space: {free_space_gb:.1f} GB")

# Check network connectivity
try:
    response = client.ping()
    print(f"Network latency: {response.latency_ms}ms")
except NetworkError:
    print("Network connectivity issues")
```

#### 3. Parsing Errors
```python
# Validate file before parsing
if parser.validate_file('manifest.safe'):
    metadata = parser.parse_metadata('manifest.safe')
else:
    print("Invalid or corrupted file")
```

## Next Steps

After completing this guide, you should:
1. ✅ Have SAR Project installed and configured
2. ✅ Be able to search for products
3. ✅ Successfully download metadata
4. ✅ Parse basic product information

### Continue Learning
- [Data Retrieval Guide](data-retrieval.md) - Advanced search and download techniques
- [Attribute Analysis](attribute-analysis.md) - Deep dive into product attributes  
- [Processing Workflows](processing-workflows.md) - Data processing examples
- [API Documentation](../api/) - Complete API reference

### Join the Community
- **GitHub**: Report issues and contribute
- **Discord**: Ask questions and share experiences
- **Forum**: Long-form discussions and tutorials
- **Email**: Direct support for complex issues

## Quick Reference

### Essential Commands
```python
# Initialize client
client = SARClient(api_key='your_key')

# Search products
products = client.search(start_date='2023-01-01', end_date='2023-01-31')

# Download metadata
client.download(product.id, './downloads/', format='metadata')

# Parse metadata
parser = SARParser(api_key='your_key')
metadata = parser.parse_metadata('manifest.safe')
```

### Useful Links
- [API Documentation](../api/README.md)
- [Data Schemas](../data-schemas/README.md)
- [Attribute Reference](../attributes/README.md)
- [Project Repository](https://github.com/your-org/sar-project)
