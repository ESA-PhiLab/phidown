# Download API

The Download API provides functionality to retrieve SAR product data, metadata files, and preview images with support for various download methods and resume capabilities.

## Endpoint

```http
GET /api/v1/download/{product_id}
POST /api/v1/download/batch
```

## Product Download

### Single Product Download
```http
GET /api/v1/download/{product_id}
```

#### Parameters
| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `format` | string | Download format (`full`, `metadata`, `preview`) | `full` |
| `compression` | string | Compression type (`zip`, `tar.gz`, `none`) | `zip` |
| `resume` | boolean | Support resume download | `true` |

#### Headers
```http
Authorization: Bearer <token>
Range: bytes=0-1023  # For resume support
User-Agent: SAR-Client/1.0
```

### Batch Download
```http
POST /api/v1/download/batch
Content-Type: application/json

{
    "products": [
        {
            "id": "S1A_IW_SLC__1SDV_20230101T060000_20230101T060030_045123_056789_1A2B",
            "format": "full",
            "compression": "zip"
        },
        {
            "id": "S1A_IW_SLC__1SDV_20230102T060000_20230102T060030_045124_056790_2C3D",
            "format": "metadata"
        }
    ],
    "delivery_method": "direct",
    "notification_url": "https://your-app.com/webhooks/download-complete"
}
```

## Response Formats

### Direct Download Response
```http
HTTP/1.1 200 OK
Content-Type: application/zip
Content-Length: 1073741824
Content-Disposition: attachment; filename="S1A_IW_SLC__1SDV_20230101T060000_20230101T060030_045123_056789_1A2B.zip"
Accept-Ranges: bytes

[Binary data]
```

### Download URL Response
```json
{
    "status": "success",
    "data": {
        "product_id": "S1A_IW_SLC__1SDV_20230101T060000_20230101T060030_045123_056789_1A2B",
        "download_url": "https://cdn.sar-project.org/products/...",
        "expires_at": "2023-01-01T12:00:00Z",
        "size_bytes": 1073741824,
        "checksum": {
            "md5": "5d41402abc4b2a76b9719d911017c592",
            "sha256": "2cf24dba4f21d4288094e4a5e5a5e5b99..."
        },
        "metadata": {
            "format": "full",
            "compression": "zip",
            "files_included": [
                "manifest.safe",
                "measurement/*.tiff",
                "annotation/*.xml",
                "calibration/*.xml"
            ]
        }
    }
}
```

### Batch Download Response
```json
{
    "status": "success",
    "data": {
        "batch_id": "batch_20230101_123456",
        "status": "processing",
        "products": [
            {
                "id": "S1A_IW_SLC__1SDV_20230101T060000_20230101T060030_045123_056789_1A2B",
                "status": "queued",
                "download_url": null,
                "estimated_completion": "2023-01-01T01:00:00Z"
            }
        ],
        "total_size_bytes": 2147483648,
        "estimated_completion": "2023-01-01T01:30:00Z"
    }
}
```

## Download Methods

### Direct Download
```python
import requests

response = requests.get(
    'https://api.sar-project.org/v1/download/S1A_IW_SLC__1SDV_20230101T060000_20230101T060030_045123_056789_1A2B',
    headers={'Authorization': 'Bearer your_token'},
    stream=True
)

with open('product.zip', 'wb') as f:
    for chunk in response.iter_content(chunk_size=8192):
        f.write(chunk)
```

### Resume Download
```python
import os
import requests

filename = 'product.zip'
resume_pos = os.path.getsize(filename) if os.path.exists(filename) else 0

headers = {
    'Authorization': 'Bearer your_token',
    'Range': f'bytes={resume_pos}-'
}

response = requests.get(download_url, headers=headers, stream=True)

mode = 'ab' if resume_pos > 0 else 'wb'
with open(filename, mode) as f:
    for chunk in response.iter_content(chunk_size=8192):
        f.write(chunk)
```

### Batch Download with Progress
```python
import time
from sar_project import SARClient

client = SARClient(api_key='your_api_key')

# Submit batch download
batch = client.download_batch([
    'S1A_IW_SLC__1SDV_20230101T060000_20230101T060030_045123_056789_1A2B',
    'S1A_IW_SLC__1SDV_20230102T060000_20230102T060030_045124_056790_2C3D'
])

# Monitor progress
while batch.status != 'completed':
    time.sleep(30)
    batch.refresh()
    print(f"Progress: {batch.progress_percent}%")

# Download completed files
for product in batch.products:
    if product.status == 'ready':
        client.download_file(product.download_url, f'{product.id}.zip')
```

## Python SDK Examples

### Basic Download
```python
from sar_project import SARClient

client = SARClient(api_key='your_api_key')

# Download full product
client.download(
    product_id='S1A_IW_SLC__1SDV_20230101T060000_20230101T060030_045123_056789_1A2B',
    output_dir='./downloads/',
    format='full'
)

# Download metadata only
client.download(
    product_id='S1A_IW_SLC__1SDV_20230101T060000_20230101T060030_045123_056789_1A2B',
    output_dir='./metadata/',
    format='metadata'
)
```

### Download with Progress Callback
```python
def progress_callback(downloaded, total):
    percent = (downloaded / total) * 100
    print(f"\rProgress: {percent:.1f}%", end='')

client.download(
    product_id='S1A_IW_SLC__1SDV_20230101T060000_20230101T060030_045123_056789_1A2B',
    output_dir='./downloads/',
    progress_callback=progress_callback
)
```

### Parallel Downloads
```python
import concurrent.futures
from sar_project import SARClient

client = SARClient(api_key='your_api_key')

product_ids = [
    'S1A_IW_SLC__1SDV_20230101T060000_20230101T060030_045123_056789_1A2B',
    'S1A_IW_SLC__1SDV_20230102T060000_20230102T060030_045124_056790_2C3D',
    'S1A_IW_SLC__1SDV_20230103T060000_20230103T060030_045125_056791_3E4F'
]

def download_product(product_id):
    return client.download(product_id, './downloads/')

# Download up to 3 products in parallel
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
    futures = [executor.submit(download_product, pid) for pid in product_ids]
    
    for future in concurrent.futures.as_completed(futures):
        result = future.result()
        print(f"Downloaded: {result.filename}")
```

## Download Formats

### Full Product (`format=full`)
- **Content**: Complete product data
- **Includes**: 
  - Measurement data (TIFF/NetCDF)
  - Annotation files (XML)
  - Calibration data (XML)
  - Manifest file (SAFE)
- **Size**: 500MB - 5GB per product
- **Use Case**: Full analysis and processing

### Metadata Only (`format=metadata`)
- **Content**: Product metadata and annotations
- **Includes**:
  - Manifest file (SAFE)
  - Annotation files (XML)
  - Calibration data (XML)
  - Preview images (PNG/JPEG)
- **Size**: 1-10MB per product
- **Use Case**: Quick analysis, inventory management

### Preview (`format=preview`)
- **Content**: Visual preview and basic metadata
- **Includes**:
  - Quick-look image (PNG)
  - Basic metadata (JSON)
- **Size**: <1MB per product
- **Use Case**: Visual inspection, thumbnail generation

## File Organization

### Default Structure
```
downloads/
├── S1A_IW_SLC__1SDV_20230101T060000_20230101T060030_045123_056789_1A2B.SAFE/
│   ├── manifest.safe
│   ├── measurement/
│   │   ├── s1a-iw1-slc-vv-*.tiff
│   │   ├── s1a-iw2-slc-vv-*.tiff
│   │   └── s1a-iw3-slc-vv-*.tiff
│   ├── annotation/
│   │   ├── calibration/
│   │   └── *.xml
│   └── preview/
│       └── quick-look.png
```

### Custom Organization
```python
# Custom file naming and organization
client.download(
    product_id='...',
    output_dir='./data/',
    filename_pattern='{platform}_{date}_{orbit}_{swath}.zip',
    extract=True,
    organize_by='date'  # date, platform, orbit
)
```

## Quality Verification

### Checksum Verification
```python
import hashlib

def verify_download(filepath, expected_md5):
    """Verify downloaded file integrity"""
    with open(filepath, 'rb') as f:
        file_hash = hashlib.md5()
        for chunk in iter(lambda: f.read(4096), b""):
            file_hash.update(chunk)
    
    return file_hash.hexdigest() == expected_md5

# Download with verification
result = client.download(product_id, './downloads/')
if verify_download(result.filepath, result.checksum['md5']):
    print("Download verified successfully")
else:
    print("Download verification failed")
```

### File Completeness Check
```python
def check_file_completeness(safe_dir):
    """Check if all expected files are present"""
    required_files = [
        'manifest.safe',
        'measurement/*.tiff',
        'annotation/*.xml'
    ]
    
    missing_files = []
    for pattern in required_files:
        if not glob.glob(os.path.join(safe_dir, pattern)):
            missing_files.append(pattern)
    
    return len(missing_files) == 0, missing_files
```

## Error Handling

### Common Error Codes
| Code | Description | HTTP Status |
|------|-------------|-------------|
| `PRODUCT_NOT_FOUND` | Product ID does not exist | 404 |
| `PRODUCT_UNAVAILABLE` | Product temporarily unavailable | 503 |
| `INSUFFICIENT_QUOTA` | Download quota exceeded | 402 |
| `DOWNLOAD_EXPIRED` | Download URL has expired | 410 |
| `INVALID_RANGE` | Invalid byte range header | 416 |
| `NETWORK_ERROR` | Network connectivity issue | 500 |

### Error Recovery
```python
import time
from sar_project.exceptions import DownloadError, NetworkError

max_retries = 3
retry_delay = 5

for attempt in range(max_retries):
    try:
        result = client.download(product_id, './downloads/')
        break
    except NetworkError as e:
        if attempt < max_retries - 1:
            print(f"Network error, retrying in {retry_delay}s...")
            time.sleep(retry_delay)
            retry_delay *= 2  # Exponential backoff
        else:
            raise e
    except DownloadError as e:
        print(f"Download failed: {e}")
        break
```

## Rate Limiting and Quotas

### Download Limits
- **Concurrent Downloads**: 5 per user
- **Daily Quota**: 100GB per user
- **Monthly Quota**: 1TB per user
- **Batch Size**: 50 products maximum

### Quota Management
```python
# Check quota status
quota = client.get_quota_status()
print(f"Used: {quota.used_gb}GB / {quota.limit_gb}GB")
print(f"Remaining: {quota.remaining_gb}GB")

# Monitor usage during download
def quota_aware_download(product_ids):
    for product_id in product_ids:
        quota = client.get_quota_status()
        if quota.remaining_gb < 5:  # Less than 5GB remaining
            print("Warning: Low quota remaining")
            break
        
        client.download(product_id, './downloads/')
```

## Related Documentation
- [API Overview](README.md)
- [Search API](search-api.md)
- [Parser API](parser-api.md)
- [User Guides](../user-guides/data-retrieval.md)
