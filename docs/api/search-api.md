# Search API

The Search API provides powerful functionality to discover and filter SAR products based on various criteria including temporal, spatial, and product-specific parameters.

## Endpoint

```http
GET /api/v1/search
POST /api/v1/search
```

## Parameters

### Temporal Parameters
| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `start_date` | string | Start date (ISO 8601) | `2023-01-01` |
| `end_date` | string | End date (ISO 8601) | `2023-01-31` |
| `date_type` | string | Date type (`sensing`, `ingestion`) | `sensing` |

### Spatial Parameters
| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `bbox` | array | Bounding box [west, south, east, north] | `[-10, 35, 5, 45]` |
| `geometry` | object | GeoJSON geometry | `{"type": "Polygon", ...}` |
| `intersects` | string | WKT geometry | `POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))` |

### Product Parameters
| Parameter | Type | Description | Values |
|-----------|------|-------------|--------|
| `product_type` | string | Product processing level | `RAW`, `SLC`, `GRD` |
| `platform` | string | Satellite platform | `S1A`, `S1B` |
| `instrument_mode` | string | Acquisition mode | `SM`, `IW`, `EW`, `WV` |
| `polarization` | string | Polarization mode | `HH`, `VV`, `HV`, `VH` |
| `swath` | string | Swath identifier | `S1`, `S2`, `S3`, `S4`, `S5`, `S6` |

### Quality Parameters
| Parameter | Type | Description | Values |
|-----------|------|-------------|--------|
| `cloud_coverage` | number | Maximum cloud coverage % | `0-100` |
| `data_quality` | string | Quality assessment | `GOOD`, `FAIR`, `POOR` |
| `processing_level` | string | Processing completeness | `L0`, `L1`, `L2` |

### Pagination Parameters
| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `page` | integer | Page number | `1` |
| `per_page` | integer | Results per page | `50` |
| `sort` | string | Sort field | `sensing_date` |
| `order` | string | Sort order | `desc` |

## Request Examples

### Basic Search (GET)
```http
GET /api/v1/search?start_date=2023-01-01&end_date=2023-01-31&product_type=SLC
```

### Advanced Search (POST)
```http
POST /api/v1/search
Content-Type: application/json

{
    "temporal": {
        "start_date": "2023-01-01",
        "end_date": "2023-01-31",
        "date_type": "sensing"
    },
    "spatial": {
        "bbox": [-10, 35, 5, 45]
    },
    "product": {
        "product_type": "SLC",
        "platform": "S1A",
        "instrument_mode": "IW",
        "polarization": "VV"
    },
    "quality": {
        "data_quality": "GOOD"
    },
    "pagination": {
        "page": 1,
        "per_page": 20
    }
}
```

### Geometry-based Search
```http
POST /api/v1/search
Content-Type: application/json

{
    "spatial": {
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [-10, 35],
                [5, 35],
                [5, 45],
                [-10, 45],
                [-10, 35]
            ]]
        }
    },
    "product": {
        "product_type": "SLC"
    }
}
```

## Response Format

### Success Response
```json
{
    "status": "success",
    "data": {
        "products": [
            {
                "id": "S1A_IW_SLC__1SDV_20230101T060000_20230101T060030_045123_056789_1A2B",
                "title": "S1A_IW_SLC__1SDV_20230101T060000_20230101T060030_045123_056789_1A2B",
                "platform": "S1A",
                "instrument_mode": "IW",
                "product_type": "SLC",
                "processing_level": "L1",
                "polarization": "VV",
                "swath": "IW",
                "sensing_date": "2023-01-01T06:00:00Z",
                "ingestion_date": "2023-01-01T12:00:00Z",
                "orbit_number": 45123,
                "relative_orbit": 123,
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[...]]
                },
                "footprint": "POLYGON((-10 35, 5 35, 5 45, -10 45, -10 35))",
                "size_mb": 1024.5,
                "cloud_coverage": 5.2,
                "data_quality": "GOOD",
                "download_url": "https://api.sar-project.org/v1/download/...",
                "metadata_url": "https://api.sar-project.org/v1/metadata/...",
                "attributes": {
                    "range_looks": 1,
                    "azimuth_looks": 1,
                    "incidence_angle": 35.5,
                    "range_resolution": 5.0,
                    "azimuth_resolution": 20.0
                }
            }
        ]
    },
    "pagination": {
        "page": 1,
        "per_page": 50,
        "total": 1247,
        "pages": 25,
        "has_next": true,
        "has_prev": false
    },
    "message": "Search completed successfully",
    "timestamp": "2023-01-01T00:00:00Z"
}
```

### Error Response
```json
{
    "status": "error",
    "error": {
        "code": "INVALID_DATE_RANGE",
        "message": "End date must be after start date",
        "details": {
            "start_date": "2023-01-31",
            "end_date": "2023-01-01"
        }
    },
    "timestamp": "2023-01-01T00:00:00Z"
}
```

## Python SDK Examples

### Basic Search
```python
from sar_project import SARClient

client = SARClient(api_key='your_api_key')

# Simple search
results = client.search(
    start_date='2023-01-01',
    end_date='2023-01-31',
    product_type='SLC'
)

print(f"Found {len(results)} products")
for product in results:
    print(f"- {product.id}")
```

### Advanced Search with Filtering
```python
# Complex search with multiple criteria
results = client.search(
    temporal={
        'start_date': '2023-01-01',
        'end_date': '2023-01-31'
    },
    spatial={
        'bbox': [-10, 35, 5, 45]
    },
    product={
        'product_type': 'SLC',
        'platform': 'S1A',
        'instrument_mode': 'IW',
        'polarization': 'VV'
    },
    quality={
        'data_quality': 'GOOD',
        'cloud_coverage': {'max': 10}
    }
)
```

### Pagination
```python
# Iterate through all pages
page = 1
all_products = []

while True:
    results = client.search(
        start_date='2023-01-01',
        end_date='2023-01-31',
        page=page,
        per_page=100
    )
    
    all_products.extend(results.products)
    
    if not results.has_next:
        break
    
    page += 1

print(f"Total products: {len(all_products)}")
```

### Geometry-based Search
```python
from shapely.geometry import Polygon

# Define area of interest
aoi = Polygon([
    (-10, 35), (5, 35), (5, 45), (-10, 45), (-10, 35)
])

results = client.search(
    geometry=aoi,
    product_type='SLC',
    start_date='2023-01-01',
    end_date='2023-01-31'
)
```

## Error Codes

| Code | Description | HTTP Status |
|------|-------------|-------------|
| `INVALID_DATE_FORMAT` | Date not in ISO 8601 format | 400 |
| `INVALID_DATE_RANGE` | End date before start date | 400 |
| `INVALID_BBOX` | Bounding box format error | 400 |
| `INVALID_GEOMETRY` | GeoJSON geometry error | 400 |
| `INVALID_PRODUCT_TYPE` | Unknown product type | 400 |
| `INVALID_PLATFORM` | Unknown platform | 400 |
| `PAGINATION_ERROR` | Invalid page parameters | 400 |
| `RATE_LIMIT_EXCEEDED` | Too many requests | 429 |
| `INTERNAL_ERROR` | Server error | 500 |

## Performance Tips

### Query Optimization
1. **Use specific date ranges**: Avoid overly broad temporal queries
2. **Limit spatial extent**: Use bounding boxes instead of complex geometries
3. **Filter early**: Apply product type and platform filters first
4. **Use pagination**: Don't retrieve all results at once

### Caching
```python
# Enable response caching
client = SARClient(
    api_key='your_api_key',
    cache_enabled=True,
    cache_ttl=3600  # 1 hour
)
```

### Asynchronous Requests
```python
import asyncio
from sar_project import AsyncSARClient

async def search_multiple_areas():
    client = AsyncSARClient(api_key='your_api_key')
    
    tasks = []
    for bbox in area_list:
        task = client.search(bbox=bbox, product_type='SLC')
        tasks.append(task)
    
    results = await asyncio.gather(*tasks)
    return results
```

## Related Documentation
- [API Overview](README.md)
- [Download API](download-api.md)
- [Parser API](parser-api.md)
- [Data Schemas](../data-schemas/)
