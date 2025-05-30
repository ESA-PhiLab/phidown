# Product Types Reference

This document provides detailed information about Sentinel-1 SAR product types supported by the SAR project.

## Overview

Sentinel-1 generates various product types depending on the acquisition mode, processing level, and intended use case. This reference covers all product types discovered in the attribute analysis.

## Product Type Naming Convention

Sentinel-1 product types follow the ESA naming convention:
```
[MODE]_[PRODUCT]__[RESOLUTION][LEVEL]
```

Where:
- **MODE**: Acquisition mode (SM, IW, EW, WV, S1-S6)
- **PRODUCT**: Product type (SLC, GRD, OCN)
- **RESOLUTION**: Resolution class (F, H, M)
- **LEVEL**: Processing level (0, 1, 2)

## Supported Product Types

### 1. Single Look Complex (SLC) Products

#### S1_SLC__1S
- **Full Name**: S1 Swath Single Look Complex Level 1
- **Description**: High-resolution SLC data from S1 swath
- **Characteristics**:
  - Complex-valued pixels
  - Preserves phase information
  - Single swath coverage
  - Suitable for interferometry

#### S2_SLC__1S
- **Full Name**: S2 Swath Single Look Complex Level 1
- **Description**: High-resolution SLC data from S2 swath
- **Characteristics**:
  - Complex-valued pixels
  - Preserves phase information
  - S2 swath geometry
  - Optimal for narrow swath applications

#### S3_SLC__1S
- **Full Name**: S3 Swath Single Look Complex Level 1
- **Description**: High-resolution SLC data from S3 swath
- **Characteristics**:
  - Complex-valued pixels
  - Preserves phase information
  - S3 swath configuration
  - Intermediate swath coverage

#### S4_SLC__1S
- **Full Name**: S4 Swath Single Look Complex Level 1
- **Description**: High-resolution SLC data from S4 swath
- **Characteristics**:
  - Complex-valued pixels
  - Preserves phase information
  - S4 swath geometry
  - Wide swath coverage

#### S5_SLC__1S
- **Full Name**: S5 Swath Single Look Complex Level 1
- **Description**: High-resolution SLC data from S5 swath
- **Characteristics**:
  - Complex-valued pixels
  - Preserves phase information
  - S5 swath configuration
  - Extended coverage

#### S6_SLC__1S
- **Full Name**: S6 Swath Single Look Complex Level 1
- **Description**: High-resolution SLC data from S6 swath
- **Characteristics**:
  - Complex-valued pixels
  - Preserves phase information
  - S6 swath geometry
  - Maximum swath width

#### IW_SLC__1S
- **Full Name**: Interferometric Wide Swath Single Look Complex Level 1
- **Description**: Standard wide swath SLC product
- **Characteristics**:
  - Three sub-swaths (IW1, IW2, IW3)
  - 250 km swath width
  - 5m x 20m resolution
  - Primary operational mode

#### EW_SLC__1S
- **Full Name**: Extra Wide Swath Single Look Complex Level 1
- **Description**: Extended coverage SLC product
- **Characteristics**:
  - Five sub-swaths (EW1-EW5)
  - 400 km swath width
  - 20m x 40m resolution
  - Maritime and polar monitoring

#### WV_SLC__1S
- **Full Name**: Wave Mode Single Look Complex Level 1
- **Description**: Ocean wave monitoring SLC product
- **Characteristics**:
  - 20 km x 20 km vignettes
  - 5m x 5m resolution
  - Ocean wave analysis
  - Acquired over open ocean

## Product Characteristics Comparison

| Product Type | Swath Width | Resolution | Primary Use Case |
|-------------|-------------|------------|------------------|
| S1_SLC__1S | ~80 km | 5m x 5m | High-resolution imaging |
| S2_SLC__1S | ~80 km | 5m x 5m | High-resolution imaging |
| S3_SLC__1S | ~80 km | 5m x 5m | High-resolution imaging |
| S4_SLC__1S | ~80 km | 5m x 5m | High-resolution imaging |
| S5_SLC__1S | ~80 km | 5m x 5m | High-resolution imaging |
| S6_SLC__1S | ~80 km | 5m x 5m | High-resolution imaging |
| IW_SLC__1S | 250 km | 5m x 20m | Standard operations |
| EW_SLC__1S | 400 km | 20m x 40m | Wide area coverage |
| WV_SLC__1S | 20km x 20km | 5m x 5m | Ocean monitoring |

## Processing Level Information

### Level 1 Products
All discovered product types are Level 1, which means:
- **Focused SAR data**: Complex-valued pixels
- **Geo-referenced**: Products are geo-located
- **Calibrated**: Radiometric calibration applied
- **Phase preserved**: Suitable for interferometry
- **Single look**: No multi-looking applied

## Data Format Specifications

### File Structure
SLC products are delivered in SAFE format containing:
- **Annotation files**: XML metadata
- **Measurement files**: Binary SAR data
- **Calibration files**: Radiometric calibration data
- **Noise files**: Noise characterization data
- **Preview files**: Quick-look images

### Data Organization
```
[PRODUCT_NAME].SAFE/
├── annotation/
│   ├── calibration/
│   ├── rfi/
│   └── [swath]_[pol]_[timestamp].xml
├── measurement/
│   └── [swath]_[pol]_[timestamp].tiff
└── preview/
    └── [preview_files]
```

## Product Selection Guidelines

### For Interferometry
- **Recommended**: IW_SLC__1S (standard operations)
- **Alternative**: S1-S6_SLC__1S (specific swath requirements)
- **Requirements**: Same orbit direction, similar temporal baseline

### For Ocean Monitoring
- **Recommended**: WV_SLC__1S (wave analysis)
- **Alternative**: EW_SLC__1S (wide coverage)
- **Requirements**: Open ocean areas, low noise

### For Land Applications
- **Recommended**: IW_SLC__1S (balanced coverage/resolution)
- **Alternative**: S1-S6_SLC__1S (high resolution)
- **Requirements**: Terrain-dependent selection

### For Polar Monitoring
- **Recommended**: EW_SLC__1S (wide coverage)
- **Alternative**: IW_SLC__1S (standard operations)
- **Requirements**: Extended coverage for ice monitoring

## Usage Examples

### Product Type Filtering
```python
# Filter by specific swath
s1_products = df[df['productType'] == 'S1_SLC__1S']

# Filter by operational mode
iw_products = df[df['productType'] == 'IW_SLC__1S']

# Get all SLC products
slc_products = df[df['productType'].str.contains('SLC')]
```

### Product Type Analysis
```python
# Analyze product type distribution
product_stats = df['productType'].value_counts()

# Group by acquisition mode
df['mode'] = df['productType'].str.extract(r'^([A-Z0-9]+)_')
mode_distribution = df['mode'].value_counts()
```

## Related Documentation

- [Sentinel-1 Attributes](sentinel-1-attributes.md) - Complete attribute reference
- [Swath Configurations](swath-configurations.md) - Swath-specific details
- [Data Schemas Overview](README.md) - Schema documentation
- [User Guides](../user-guides/README.md) - Product selection guidance

---

*Product type availability depends on Sentinel-1 operational planning and may vary by geographic region and time period.*
