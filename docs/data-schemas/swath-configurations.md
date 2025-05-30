# Swath Configurations

This document provides detailed information about Sentinel-1 SAR swath configurations (S1-S6) and their operational characteristics.

## Overview

Sentinel-1 SAR operates with different swath configurations depending on the acquisition mode and geometry. Each swath represents a specific imaging geometry with unique characteristics for range resolution, azimuth resolution, and coverage.

## Swath Types

### S1 Swath
- **Description**: Near-range swath with highest resolution
- **Range Resolution**: ~5-20m (depending on mode)
- **Azimuth Resolution**: ~5-20m
- **Typical Use Cases**: 
  - High-resolution coastal monitoring
  - Urban area mapping
  - Infrastructure monitoring

### S2 Swath
- **Description**: Mid-range swath balancing resolution and coverage
- **Range Resolution**: ~10-25m
- **Azimuth Resolution**: ~10-25m
- **Typical Use Cases**:
  - Agricultural monitoring
  - Land cover classification
  - Environmental studies

### S3 Swath
- **Description**: Mid to far-range swath
- **Range Resolution**: ~15-30m
- **Azimuth Resolution**: ~15-30m
- **Typical Use Cases**:
  - Regional monitoring
  - Forestry applications
  - Geological surveys

### S4 Swath
- **Description**: Far-range swath with extended coverage
- **Range Resolution**: ~20-40m
- **Azimuth Resolution**: ~20-40m
- **Typical Use Cases**:
  - Wide-area monitoring
  - Climate studies
  - Large-scale mapping

### S5 Swath
- **Description**: Very far-range swath
- **Range Resolution**: ~25-50m
- **Azimuth Resolution**: ~25-50m
- **Typical Use Cases**:
  - Continental monitoring
  - Ocean observations
  - Ice sheet monitoring

### S6 Swath
- **Description**: Extreme far-range swath with maximum coverage
- **Range Resolution**: ~30-60m
- **Azimuth Resolution**: ~30-60m
- **Typical Use Cases**:
  - Global monitoring
  - Climate change studies
  - Large-scale oceanography

## Operational Modes

### Stripmap (SM) Mode
- **Available Swaths**: S1, S2, S3, S4, S5, S6
- **Swath Width**: ~80km
- **Resolution**: 5m × 5m
- **Coverage**: Single swath per pass

### Interferometric Wide Swath (IW) Mode
- **Sub-swaths**: IW1, IW2, IW3
- **Combined Swath Width**: ~250km
- **Resolution**: 5m × 20m
- **Coverage**: Default acquisition mode over land

### Extra Wide Swath (EW) Mode
- **Sub-swaths**: EW1, EW2, EW3, EW4, EW5
- **Combined Swath Width**: ~400km
- **Resolution**: 20m × 40m
- **Coverage**: Wide coverage mode

### Wave (WV) Mode
- **Swath**: Specific wave imaging
- **Resolution**: 5m × 5m
- **Coverage**: Small imagettes (20km × 20km)

## Technical Specifications

### Frequency and Polarization
- **Frequency Band**: C-band (5.405 GHz)
- **Polarizations**: 
  - Single: HH or VV
  - Dual: HH+HV, VV+VH
  - Full: HH+HV+VH+VV (limited cases)

### Geometric Parameters
```yaml
swath_parameters:
  S1:
    incidence_angle: "20-25°"
    range_looks: 1-5
    azimuth_looks: 1-5
    
  S2:
    incidence_angle: "25-30°"
    range_looks: 1-5
    azimuth_looks: 1-5
    
  S3:
    incidence_angle: "30-35°"
    range_looks: 1-5
    azimuth_looks: 1-5
    
  S4:
    incidence_angle: "35-40°"
    range_looks: 1-5
    azimuth_looks: 1-5
    
  S5:
    incidence_angle: "40-45°"
    range_looks: 1-5
    azimuth_looks: 1-5
    
  S6:
    incidence_angle: "45-50°"
    range_looks: 1-5
    azimuth_looks: 1-5
```

## Swath Selection Guidelines

### High Resolution Requirements
- **Recommended**: S1, S2
- **Applications**: Urban mapping, infrastructure monitoring
- **Trade-offs**: Smaller coverage area

### Balanced Resolution and Coverage
- **Recommended**: S2, S3, S4
- **Applications**: Agricultural monitoring, environmental studies
- **Trade-offs**: Moderate resolution and coverage

### Wide Coverage Requirements
- **Recommended**: S4, S5, S6
- **Applications**: Regional monitoring, climate studies
- **Trade-offs**: Lower resolution but larger coverage

## Data Processing Considerations

### Multi-swath Processing
```python
# Example: Processing multiple swaths
swaths = ['S1', 'S2', 'S3']
for swath in swaths:
    process_swath_data(swath)
    apply_geometric_correction(swath)
    merge_swath_products(swath)
```

### Swath Mosaicking
- **Purpose**: Combine multiple swaths for continuous coverage
- **Challenges**: Different incidence angles, resolution matching
- **Solutions**: Radiometric normalization, geometric alignment

### Quality Assessment
- **Metrics**: Signal-to-noise ratio, phase coherence
- **Validation**: Cross-swath consistency checks
- **Reporting**: Per-swath quality statistics

## File Naming Conventions

### Swath Identification in Filenames
```
S1A_[MODE]_[TYPE]_[RESOLUTION]_[START_TIME]_[END_TIME]_[ORBIT]_[DATA_TAKE]_[PRODUCT_ID].SAFE

Examples:
- S1A_S1_SLC_1SDV_20230101T060000_20230101T060030_045123_056789_1A2B.SAFE
- S1A_S2_RAW_0SDH_20230101T060000_20230101T060030_045123_056789_2C3D.SAFE
```

### Swath-specific Metadata
- **Location**: Product XML files
- **Content**: Geometric parameters, acquisition settings
- **Access**: Via metadata parsers and APIs

## Common Use Cases

### Research Applications
1. **Time Series Analysis**: Multi-temporal swath comparison
2. **Interferometry**: Phase difference analysis between swaths
3. **Polarimetry**: Multi-polarization swath analysis

### Operational Applications
1. **Disaster Monitoring**: Rapid swath selection for emergency response
2. **Agricultural Monitoring**: Seasonal swath coverage planning
3. **Maritime Surveillance**: Optimal swath for vessel detection

## Quality Control

### Swath-specific Validation
- **Geometric accuracy**: Sub-pixel registration between swaths
- **Radiometric consistency**: Cross-swath calibration
- **Temporal stability**: Long-term swath performance monitoring

### Error Detection
- **Missing data**: Swath coverage gaps
- **Geometric distortions**: Layover and shadow effects
- **Radiometric anomalies**: Calibration drift

## Related Documentation
- [Sentinel-1 Attributes](sentinel-1-attributes.md)
- [Product Types](product-types.md)
- [Data Schema Overview](README.md)
