# Attribute References

This section provides detailed documentation for all SAR product attributes, organized by swath and product type.

## Overview

SAR products contain numerous attributes that describe acquisition parameters, processing settings, quality metrics, and geometric characteristics. This documentation provides comprehensive reference information for all available attributes.

## Attribute Categories

### Basic Product Information
- **Product Identification**: ID, title, platform, mission
- **Temporal Information**: Sensing time, processing time, validity period
- **Spatial Information**: Footprint, center coordinates, coverage area
- **Product Classification**: Type, level, class, category

### Technical Parameters
- **Acquisition Settings**: Mode, polarization, swath configuration
- **Geometric Parameters**: Incidence angle, look direction, orbit parameters
- **Processing Parameters**: Range/azimuth looks, resolution, pixel spacing
- **Calibration Information**: Calibration factors, noise levels

### Quality Metrics
- **Data Quality**: Overall quality assessment, completeness
- **Radiometric Quality**: Accuracy, stability, noise characteristics
- **Geometric Quality**: Registration accuracy, distortion metrics
- **Phase Quality**: Coherence, phase noise (for SLC products)

## Swath-Specific Attributes

| Swath | Attributes | Documentation |
|-------|------------|---------------|
| **S1** | 145 attributes | [S1 Attributes](s1-attributes.md) |
| **S2** | 142 attributes | [S2 Attributes](s2-attributes.md) |
| **S3** | 138 attributes | [S3 Attributes](s3-attributes.md) |
| **S4** | 135 attributes | [S4 Attributes](s4-attributes.md) |
| **S5** | 133 attributes | [S5 Attributes](s5-attributes.md) |
| **S6** | 131 attributes | [S6 Attributes](s6-attributes.md) |

## Product Type Attributes

### RAW Products
- **Raw Data Characteristics**: Unprocessed radar data
- **Acquisition Parameters**: Original sensor settings
- **Timing Information**: Precise timing data
- **Orbit Information**: Detailed orbital parameters

### SLC Products
- **Complex Data**: I/Q components, phase information
- **Geometric Correction**: Range/Doppler correction
- **Radiometric Calibration**: Calibrated backscatter values
- **Quality Assessment**: Phase quality metrics

### GRD Products
- **Multi-looking**: Range and azimuth averaging
- **Geometric Correction**: Map projection parameters
- **Radiometric Normalization**: Terrain correction factors
- **Output Format**: Amplitude-only data

## Common Attributes Reference

### Essential Attributes
```yaml
# Most commonly used attributes across all products
essential_attributes:
  - platform                 # S1A, S1B
  - instrument_mode          # SM, IW, EW, WV
  - product_type            # RAW, SLC, GRD
  - processing_level        # L0, L1, L2
  - polarization           # HH, VV, HV, VH
  - swath                  # S1-S6, IW1-IW3, EW1-EW5
  - sensing_start_time     # Acquisition start
  - sensing_stop_time      # Acquisition end
  - orbit_number          # Absolute orbit
  - relative_orbit        # Relative orbit (1-175)
  - pass_direction        # ASCENDING, DESCENDING
```

### Geometric Attributes
```yaml
geometric_attributes:
  - footprint             # Product boundary (WKT)
  - center_coordinates    # Product center [lon, lat]
  - incidence_angle      # Radar incidence angle
  - range_resolution     # Ground range resolution (m)
  - azimuth_resolution   # Azimuth resolution (m)
  - pixel_spacing_range  # Range pixel spacing (m)
  - pixel_spacing_azimuth # Azimuth pixel spacing (m)
  - range_looks          # Number of range looks
  - azimuth_looks        # Number of azimuth looks
```

### Quality Attributes
```yaml
quality_attributes:
  - data_quality              # GOOD, FAIR, POOR
  - noise_equivalent_sigma0   # Noise floor (dB)
  - radiometric_accuracy     # Calibration accuracy
  - geometric_accuracy       # Positioning accuracy
  - phase_quality           # Phase coherence (SLC only)
  - missing_lines           # Data gaps
  - duplicated_lines        # Duplicate data
```

## Attribute Data Types

### String Attributes
- **Platform**: `S1A`, `S1B`
- **Mode**: `SM`, `IW`, `EW`, `WV`
- **Polarization**: `HH`, `VV`, `HV`, `VH`
- **Quality**: `EXCELLENT`, `GOOD`, `FAIR`, `POOR`

### Numeric Attributes
- **Integer**: Orbit numbers, line counts, pixel counts
- **Float**: Angles, resolutions, coordinates, quality metrics
- **Double**: Precise timing, frequencies, large measurements

### Temporal Attributes
- **DateTime**: ISO 8601 format (`YYYY-MM-DDTHH:MM:SS.ssssssZ`)
- **Duration**: Time intervals in seconds or milliseconds
- **Relative Time**: Offsets from reference times

### Geometric Attributes
- **Coordinates**: Decimal degrees (WGS84)
- **Footprints**: Well-Known Text (WKT) format
- **Angles**: Degrees from standard references
- **Distances**: Meters or kilometers

## Attribute Validation Rules

### Value Constraints
```python
validation_rules = {
    'platform': {
        'type': 'string',
        'allowed_values': ['S1A', 'S1B'],
        'required': True
    },
    'orbit_number': {
        'type': 'integer',
        'min_value': 1,
        'max_value': 999999,
        'required': True
    },
    'incidence_angle': {
        'type': 'float',
        'min_value': 15.0,
        'max_value': 50.0,
        'unit': 'degrees'
    },
    'sensing_start_time': {
        'type': 'datetime',
        'format': 'ISO8601',
        'min_date': '2014-04-01T00:00:00Z',
        'required': True
    }
}
```

### Cross-Attribute Validation
```python
cross_validation = {
    'temporal_consistency': {
        'rule': 'sensing_stop_time > sensing_start_time',
        'error': 'Stop time must be after start time'
    },
    'swath_mode_compatibility': {
        'rule': 'swath in allowed_swaths[instrument_mode]',
        'error': 'Swath not valid for instrument mode'
    },
    'resolution_consistency': {
        'rule': 'range_resolution <= pixel_spacing_range * 2',
        'error': 'Resolution cannot exceed 2x pixel spacing'
    }
}
```

## Usage Examples

### Basic Attribute Access
```python
from sar_project import SARParser

parser = SARParser(api_key='your_api_key')

# Parse product metadata
metadata = parser.parse_metadata('manifest.safe')

# Access common attributes
print(f"Platform: {metadata.platform}")
print(f"Mode: {metadata.instrument_mode}")
print(f"Sensing Time: {metadata.sensing_start_time}")
print(f"Orbit: {metadata.orbit_number}")
```

### Attribute Filtering
```python
# Filter products by attributes
def filter_by_attributes(products, filters):
    """Filter products based on attribute criteria"""
    filtered = []
    
    for product in products:
        match = True
        for attr, criteria in filters.items():
            value = getattr(product, attr, None)
            
            if 'equals' in criteria and value != criteria['equals']:
                match = False
                break
            if 'min' in criteria and value < criteria['min']:
                match = False
                break
            if 'max' in criteria and value > criteria['max']:
                match = False
                break
            if 'in' in criteria and value not in criteria['in']:
                match = False
                break
        
        if match:
            filtered.append(product)
    
    return filtered

# Apply attribute filters
filters = {
    'platform': {'in': ['S1A']},
    'instrument_mode': {'equals': 'IW'},
    'incidence_angle': {'min': 30, 'max': 40},
    'data_quality': {'in': ['GOOD', 'EXCELLENT']}
}

filtered_products = filter_by_attributes(products, filters)
```

### Attribute Statistics
```python
import pandas as pd

def analyze_attributes(products, attributes):
    """Generate statistics for product attributes"""
    
    data = []
    for product in products:
        row = {}
        for attr in attributes:
            row[attr] = getattr(product, attr, None)
        data.append(row)
    
    df = pd.DataFrame(data)
    
    # Generate statistics
    stats = {}
    for attr in attributes:
        if df[attr].dtype in ['int64', 'float64']:
            stats[attr] = {
                'mean': df[attr].mean(),
                'std': df[attr].std(),
                'min': df[attr].min(),
                'max': df[attr].max(),
                'count': df[attr].count()
            }
        else:
            stats[attr] = {
                'unique_values': df[attr].nunique(),
                'most_common': df[attr].mode().iloc[0] if not df[attr].empty else None,
                'count': df[attr].count()
            }
    
    return stats

# Analyze key attributes
key_attributes = [
    'platform', 'instrument_mode', 'orbit_number',
    'incidence_angle', 'range_resolution', 'data_quality'
]

attribute_stats = analyze_attributes(products, key_attributes)
```

## Attribute Evolution

### Version History
- **V1.0** (2014): Initial Sentinel-1 attribute set
- **V1.1** (2016): Added quality metrics, improved calibration
- **V1.2** (2018): Extended geometric attributes, phase quality
- **V1.3** (2020): Enhanced processing parameters
- **V1.4** (2022): New validation rules, derived attributes

### Deprecated Attributes
| Attribute | Deprecated | Replacement | Notes |
|-----------|------------|-------------|-------|
| `old_quality_flag` | V1.2 | `data_quality` | Simplified quality assessment |
| `legacy_orbit_ref` | V1.3 | `orbit_number` | Standardized orbit reference |
| `processing_version_old` | V1.4 | `processing_baseline` | Updated versioning scheme |

## Best Practices

### Attribute Selection
1. **Use essential attributes** for basic filtering and sorting
2. **Include quality attributes** for data validation
3. **Add geometric attributes** for spatial analysis
4. **Consider temporal attributes** for time series

### Performance Tips
1. **Cache frequently accessed attributes** to avoid repeated parsing
2. **Use batch attribute extraction** for multiple products
3. **Filter at query time** rather than post-processing
4. **Index attributes** in databases for fast searches

### Quality Assurance
1. **Validate attribute ranges** against known limits
2. **Check cross-attribute consistency** for logical relationships
3. **Monitor attribute completeness** across product collections
4. **Flag anomalous values** for manual review

## Related Documentation
- [S1 Swath Attributes](s1-attributes.md)
- [Data Schemas](../data-schemas/README.md)
- [Parser API](../api/parser-api.md)
- [User Guides](../user-guides/)
