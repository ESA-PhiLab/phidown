# SAR Project API Documentation

## Overview

This document provides comprehensive API documentation for the SAR (Synthetic Aperture Radar) data analysis project. The APIs enable programmatic access to Sentinel-1 SAR SLC product attributes, search functionality, and data retrieval capabilities.

## Table of Contents

1. [Authentication](#authentication)
2. [Search API](#search-api)
3. [Attribute API](#attribute-api)
4. [Download API](#download-api)
5. [Parser API](#parser-api)
6. [Error Handling](#error-handling)
7. [Rate Limiting](#rate-limiting)
8. [Examples](#examples)

## Base URL

```
https://api.sar-project.org/v1
```

## Authentication

### API Key Authentication
```http
Authorization: Bearer YOUR_API_KEY
```

### Example Request
```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \\
     "https://api.sar-project.org/v1/products/search"
```

## Search API

### Search Products

Search for Sentinel-1 SLC products based on various criteria.

**Endpoint**: `GET /products/search`

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `start_date` | string | No | Start date (ISO 8601 format) |
| `end_date` | string | No | End date (ISO 8601 format) |
| `bbox` | string | No | Bounding box (WKT POLYGON) |
| `platform` | string | No | Platform name (S1A, S1B) |
| `orbit_direction` | string | No | Orbit direction (ASCENDING, DESCENDING) |
| `operational_mode` | string | No | Operational mode (SM, IW, EW, WV) |
| `relative_orbit` | integer | No | Relative orbit number (1-175) |
| `processing_level` | string | No | Processing level (L0, L1, L2) |
| `limit` | integer | No | Maximum results (default: 100, max: 1000) |
| `offset` | integer | No | Results offset (default: 0) |

#### Response Format

```json
{
  "status": "success",
  "total_results": 1250,
  "returned_results": 100,
  "offset": 0,
  "products": [
    {
      "id": "S1A_IW_SLC__1SDV_20231201T054623_20231201T054650_051234_062A8F_1234",
      "beginningDateTime": "2023-12-01T05:46:23.123456Z",
      "endingDateTime": "2023-12-01T05:46:50.987654Z",
      "coordinates": "POLYGON((-10.5 35.2, -8.3 35.2, -8.3 37.1, -10.5 37.1, -10.5 35.2))",
      "platformShortName": "S1A",
      "orbitDirection": "ASCENDING",
      "operationalMode": "IW",
      "relativeOrbitNumber": 87,
      "processingLevel": "L1",
      "processingBaseline": "003.52",
      "polarisationChannels": ["VV", "VH"]
    }
  ]
}
```
```python
from sar_project import SARClient

# Initialize client
client = SARClient()

# Search for products
products = client.search(
    start_date='2023-01-01',
    end_date='2023-01-31',
    product_type='SLC',
    polarization='VV'
)

# Download product
for product in products:
    client.download(product.id, './data/')
    
# Parse attributes
attributes = client.parse_attributes(product.metadata_file)
```

### Authentication
```python
# API key authentication
client = SARClient(api_key='your_api_key_here')

# OAuth authentication
client = SARClient.from_oauth(
    client_id='your_client_id',
    client_secret='your_client_secret'
)
```

## API Reference

### Base URL
```
https://api.sar-project.org/v1/
```

### Common Headers
```http
Content-Type: application/json
Authorization: Bearer <token>
User-Agent: SAR-Client/1.0
```

### Response Format
```json
{
    "status": "success|error",
    "data": {},
    "message": "Response message",
    "timestamp": "2023-01-01T00:00:00Z",
    "pagination": {
        "page": 1,
        "per_page": 50,
        "total": 1000,
        "pages": 20
    }
}
```

### Error Handling
```json
{
    "status": "error",
    "error": {
        "code": "INVALID_PARAMETER",
        "message": "Invalid date format",
        "details": {
            "parameter": "start_date",
            "expected": "YYYY-MM-DD",
            "received": "01/01/2023"
        }
    }
}
```

## Rate Limiting

### Default Limits
- **Search API**: 100 requests/minute
- **Download API**: 10 concurrent downloads
- **Parser API**: 1000 requests/minute

### Headers
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640995200
```

### Rate Limit Handling
```python
try:
    result = client.search(...)
except RateLimitExceeded as e:
    wait_time = e.retry_after
    time.sleep(wait_time)
    result = client.search(...)
```

## SDK Libraries

### Python SDK
```bash
pip install sar-project-sdk
```

### JavaScript SDK
```bash
npm install @sar-project/sdk
```

### R Package
```r
install.packages("sarproject")
```

## Testing

### Test Environment
```
Base URL: https://api-test.sar-project.org/v1/
```

### Sample Data
```python
# Get test data
test_client = SARClient(base_url='https://api-test.sar-project.org/v1/')
test_products = test_client.get_test_products()
```

## Monitoring and Status

### API Status Page
- URL: https://status.sar-project.org
- Real-time API health monitoring
- Historical uptime statistics

### Metrics
- **Availability**: 99.9% SLA
- **Response Time**: <200ms average
- **Throughput**: 1M+ requests/day

## Support

### Documentation
- **API Reference**: Detailed endpoint documentation
- **Code Examples**: Implementation samples
- **Tutorials**: Step-by-step guides

### Community
- **GitHub Issues**: Bug reports and feature requests
- **Discord**: Real-time community support
- **Email**: support@sar-project.org

## Changelog

### v1.2.0 (2023-12-01)
- Added batch download functionality
- Improved search performance
- New attribute filtering options

### v1.1.0 (2023-10-01)
- Enhanced error handling
- Added OAuth2 support
- Improved documentation

### v1.0.0 (2023-08-01)
- Initial stable release
- Core search and download functionality
- Basic attribute parsing

## Related Documentation
- [Search API Reference](search-api.md)
- [Download API Reference](download-api.md)
- [Parser API Reference](parser-api.md)
- [User Guides](../user-guides/)
