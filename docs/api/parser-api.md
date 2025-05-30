# Parser API

The Parser API provides functionality to extract, process, and analyze metadata and attributes from SAR product files, supporting various data formats and providing structured access to product information.

## Endpoint

```http
POST /api/v1/parse/metadata
POST /api/v1/parse/attributes
GET /api/v1/parse/schema
```

## Metadata Parsing

### Parse Product Metadata
```http
POST /api/v1/parse/metadata
Content-Type: multipart/form-data

file: manifest.safe
product_type: SLC
extract_all: true
```

#### Parameters
| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `file` | file | Metadata file (manifest.safe, .xml) | Required |
| `product_type` | string | Product type (`RAW`, `SLC`, `GRD`) | Auto-detect |
| `extract_all` | boolean | Extract all available attributes | `false` |
| `format` | string | Output format (`json`, `xml`, `csv`) | `json` |
| `validate` | boolean | Validate against schema | `true` |

### Parse Multiple Files
```http
POST /api/v1/parse/metadata/batch
Content-Type: multipart/form-data

files[]: manifest1.safe
files[]: manifest2.safe
files[]: annotation.xml
```

## Attribute Extraction

### Extract Specific Attributes
```http
POST /api/v1/parse/attributes
Content-Type: application/json

{
    "file_url": "https://storage.sar-project.org/products/.../manifest.safe",
    "attributes": [
        "platform",
        "instrument_mode", 
        "polarization",
        "orbit_number",
        "sensing_time"
    ],
    "product_type": "SLC"
}
```

### Extract All Attributes
```http
POST /api/v1/parse/attributes
Content-Type: application/json

{
    "file_url": "https://storage.sar-project.org/products/.../manifest.safe",
    "extract_all": true,
    "include_derived": true,
    "include_quality": true
}
```

## Response Formats

### Metadata Parse Response
```json
{
    "status": "success",
    "data": {
        "product_id": "S1A_IW_SLC__1SDV_20230101T060000_20230101T060030_045123_056789_1A2B",
        "file_type": "manifest.safe",
        "parsed_at": "2023-01-01T12:00:00Z",
        "metadata": {
            "basic_info": {
                "platform": "S1A",
                "instrument": "SAR-C",
                "instrument_mode": "IW",
                "product_type": "SLC",
                "processing_level": "L1",
                "product_class": "S"
            },
            "temporal": {
                "sensing_start": "2023-01-01T06:00:00.000000Z",
                "sensing_stop": "2023-01-01T06:00:30.000000Z",
                "processing_time": "2023-01-01T08:30:15.123456Z"
            },
            "spatial": {
                "footprint": "POLYGON((-10 35, 5 35, 5 45, -10 45, -10 35))",
                "center_coordinates": [47.5, -2.5],
                "coverage_area_km2": 25000.5
            },
            "orbital": {
                "orbit_number": 45123,
                "relative_orbit": 123,
                "cycle_number": 301,
                "pass_direction": "ASCENDING"
            },
            "technical": {
                "polarization": "VV",
                "swath": "IW",
                "range_looks": 1,
                "azimuth_looks": 1,
                "range_resolution_m": 5.0,
                "azimuth_resolution_m": 20.0,
                "incidence_angle_deg": 35.5,
                "pixel_spacing_range_m": 2.33,
                "pixel_spacing_azimuth_m": 14.07
            },
            "quality": {
                "data_quality": "GOOD",
                "noise_equivalent_sigma0": -22.5,
                "radiometric_accuracy": 0.5,
                "phase_quality": 0.95
            }
        },
        "validation": {
            "schema_valid": true,
            "warnings": [],
            "errors": []
        }
    }
}
```

### Attribute Extraction Response
```json
{
    "status": "success",
    "data": {
        "product_id": "S1A_IW_SLC__1SDV_20230101T060000_20230101T060030_045123_056789_1A2B",
        "extracted_at": "2023-01-01T12:00:00Z",
        "attributes": {
            "platform": {
                "value": "S1A",
                "type": "string",
                "source": "manifest.safe/metadataSection/platform",
                "confidence": 1.0
            },
            "instrument_mode": {
                "value": "IW",
                "type": "string",
                "source": "manifest.safe/metadataSection/instrumentMode",
                "confidence": 1.0
            },
            "polarization": {
                "value": "VV",
                "type": "string", 
                "source": "annotation/s1a-iw-slc-vv-*.xml",
                "confidence": 1.0
            },
            "orbit_number": {
                "value": 45123,
                "type": "integer",
                "source": "manifest.safe/metadataSection/orbitNumber",
                "confidence": 1.0
            },
            "sensing_time": {
                "value": "2023-01-01T06:00:00.000000Z",
                "type": "datetime",
                "source": "manifest.safe/metadataSection/startTime",
                "confidence": 1.0
            }
        },
        "derived_attributes": {
            "temporal_coverage_hours": 0.0083,
            "spatial_coverage_km2": 25000.5,
            "data_volume_gb": 1.2
        },
        "quality_metrics": {
            "completeness": 1.0,
            "consistency": 0.98,
            "accuracy": 0.95
        }
    }
}
```

## Python SDK Examples

### Basic Metadata Parsing
```python
from sar_project import SARParser

parser = SARParser(api_key='your_api_key')

# Parse local file
with open('manifest.safe', 'rb') as f:
    metadata = parser.parse_metadata(
        file=f,
        product_type='SLC',
        extract_all=True
    )

print(f"Platform: {metadata.basic_info.platform}")
print(f"Mode: {metadata.basic_info.instrument_mode}")
print(f"Sensing time: {metadata.temporal.sensing_start}")
```

### Attribute Extraction
```python
# Extract specific attributes
attributes = parser.extract_attributes(
    file_path='./products/manifest.safe',
    attributes=[
        'platform',
        'instrument_mode',
        'polarization',
        'orbit_number'
    ]
)

for attr_name, attr_data in attributes.items():
    print(f"{attr_name}: {attr_data.value} (confidence: {attr_data.confidence})")
```

### Batch Processing
```python
import os
from pathlib import Path

# Process all SAFE files in directory
safe_dir = Path('./products/')
results = []

for safe_file in safe_dir.glob('**/*.SAFE/manifest.safe'):
    try:
        metadata = parser.parse_metadata(file_path=str(safe_file))
        results.append({
            'file': str(safe_file),
            'product_id': metadata.basic_info.product_id,
            'platform': metadata.basic_info.platform,
            'sensing_time': metadata.temporal.sensing_start
        })
    except Exception as e:
        print(f"Error parsing {safe_file}: {e}")

# Convert to DataFrame
import pandas as pd
df = pd.DataFrame(results)
print(df)
```

### Advanced Parsing with Validation
```python
# Parse with custom validation rules
validation_rules = {
    'required_attributes': [
        'platform', 'instrument_mode', 'product_type'
    ],
    'value_constraints': {
        'platform': ['S1A', 'S1B'],
        'instrument_mode': ['SM', 'IW', 'EW', 'WV']
    },
    'temporal_constraints': {
        'min_sensing_time': '2014-04-01T00:00:00Z',
        'max_sensing_time': '2030-01-01T00:00:00Z'
    }
}

metadata = parser.parse_metadata(
    file_path='manifest.safe',
    validation_rules=validation_rules,
    strict_validation=True
)

if metadata.validation.schema_valid:
    print("Validation passed")
else:
    print("Validation errors:")
    for error in metadata.validation.errors:
        print(f"- {error}")
```

## Supported File Formats

### SAFE Manifest Files
- **File**: `manifest.safe`
- **Content**: Product overview, metadata references
- **Parsing**: XML-based extraction
- **Attributes**: Basic product information, file inventory

### Annotation Files
- **Files**: `annotation/*.xml`
- **Content**: Detailed product parameters
- **Parsing**: XML schema-based extraction
- **Attributes**: Technical parameters, calibration info

### Calibration Files
- **Files**: `annotation/calibration/*.xml`
- **Content**: Radiometric calibration data
- **Parsing**: XML with numeric data extraction
- **Attributes**: Calibration coefficients, noise levels

### Preview Files
- **Files**: `preview/*.png`, `preview/*.jpg`
- **Content**: Quick-look images
- **Parsing**: Image metadata extraction
- **Attributes**: Image dimensions, creation time

## Custom Attribute Definitions

### Define Custom Attributes
```python
# Register custom attribute extractor
@parser.register_attribute_extractor('custom_quality_score')
def extract_quality_score(manifest_tree):
    """Extract custom quality score from multiple sources"""
    noise_level = float(manifest_tree.find('.//noiseLevel').text)
    phase_quality = float(manifest_tree.find('.//phaseQuality').text)
    
    # Custom calculation
    quality_score = (phase_quality * 0.7) + ((1 - noise_level/100) * 0.3)
    
    return {
        'value': round(quality_score, 3),
        'type': 'float',
        'source': 'calculated',
        'confidence': 0.9
    }

# Use custom attribute
attributes = parser.extract_attributes(
    file_path='manifest.safe',
    attributes=['platform', 'custom_quality_score']
)
```

### Attribute Transformation
```python
# Transform attributes during extraction
transformations = {
    'sensing_time': lambda x: x.replace('T', ' ').replace('Z', ''),
    'orbit_number': lambda x: f"ORB_{x:06d}",
    'platform': lambda x: x.lower()
}

attributes = parser.extract_attributes(
    file_path='manifest.safe',
    attributes=['sensing_time', 'orbit_number', 'platform'],
    transformations=transformations
)
```

## Schema Validation

### Get Available Schemas
```http
GET /api/v1/parse/schema
```

Response:
```json
{
    "status": "success",
    "data": {
        "schemas": [
            {
                "name": "sentinel1_slc",
                "version": "1.2",
                "description": "Sentinel-1 SLC product schema",
                "attributes": 156,
                "last_updated": "2023-01-01T00:00:00Z"
            },
            {
                "name": "sentinel1_raw",
                "version": "1.1", 
                "description": "Sentinel-1 RAW product schema",
                "attributes": 98,
                "last_updated": "2022-12-01T00:00:00Z"
            }
        ]
    }
}
```

### Custom Schema Validation
```python
# Load custom schema
schema = parser.load_schema('custom_schema.json')

# Validate against custom schema
metadata = parser.parse_metadata(
    file_path='manifest.safe',
    schema=schema,
    validate=True
)

# Check validation results
if metadata.validation.schema_valid:
    print("Metadata conforms to schema")
else:
    for error in metadata.validation.errors:
        print(f"Schema error: {error}")
```

## Performance Optimization

### Caching
```python
# Enable parsing cache
parser = SARParser(
    api_key='your_api_key',
    cache_enabled=True,
    cache_dir='./parse_cache/',
    cache_ttl=86400  # 24 hours
)

# Parse with caching
metadata = parser.parse_metadata('manifest.safe')  # First call - parsed
metadata = parser.parse_metadata('manifest.safe')  # Second call - cached
```

### Parallel Processing
```python
import concurrent.futures
from pathlib import Path

def parse_safe_file(safe_path):
    return parser.parse_metadata(file_path=safe_path)

# Process multiple files in parallel
safe_files = list(Path('./products/').glob('**/*.SAFE/manifest.safe'))

with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
    futures = [executor.submit(parse_safe_file, f) for f in safe_files]
    
    results = []
    for future in concurrent.futures.as_completed(futures):
        try:
            result = future.result()
            results.append(result)
        except Exception as e:
            print(f"Parsing error: {e}")
```

### Memory Optimization
```python
# Parse large files with streaming
parser = SARParser(
    api_key='your_api_key',
    streaming=True,
    max_memory_mb=500
)

# Parse without loading entire file into memory
metadata = parser.parse_metadata_stream(
    file_path='large_manifest.safe',
    attributes=['platform', 'sensing_time']  # Only extract needed attributes
)
```

## Error Handling

### Common Parsing Errors
| Error Code | Description | Solution |
|------------|-------------|----------|
| `INVALID_FILE_FORMAT` | File format not supported | Check file extension and content |
| `CORRUPTED_METADATA` | XML parsing failed | Verify file integrity |
| `MISSING_ATTRIBUTES` | Required attributes not found | Update parser schema |
| `SCHEMA_VALIDATION_FAILED` | Metadata doesn't match schema | Check schema version |
| `ENCODING_ERROR` | Character encoding issues | Specify correct encoding |

### Error Recovery
```python
from sar_project.exceptions import ParsingError, SchemaValidationError

try:
    metadata = parser.parse_metadata('manifest.safe')
except ParsingError as e:
    print(f"Parsing failed: {e}")
    # Try alternative parsing method
    metadata = parser.parse_metadata(
        'manifest.safe',
        fallback_parser=True,
        strict_validation=False
    )
except SchemaValidationError as e:
    print(f"Schema validation failed: {e}")
    # Continue with partial data
    metadata = parser.parse_metadata(
        'manifest.safe',
        validate=False
    )
```

## Related Documentation
- [API Overview](README.md)
- [Search API](search-api.md)
- [Download API](download-api.md)
- [Data Schemas](../data-schemas/)
- [Attribute References](../attributes/)
