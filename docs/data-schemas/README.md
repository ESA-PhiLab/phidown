# SAR Data Schemas Overview

## Introduction

This document provides an overview of the data schemas used in the SAR (Synthetic Aperture Radar) project, specifically focusing on Sentinel-1 SAR SLC (Single Look Complex) data structures and attribute definitions.

## Schema Architecture

### Primary Data Schema: Sentinel-1 SLC Attributes

The core data schema is based on analysis of Sentinel-1 SAR SLC products, encompassing 26 primary attributes organized into logical categories:

```
Sentinel-1 SLC Product Attributes
├── Temporal Attributes (5)
│   ├── beginningDateTime
│   ├── endingDateTime
│   ├── completionTimeFromAscendingNode
│   ├── segmentStartTime
│   └── processingDate
├── Spatial Attributes (1)
│   └── coordinates
├── Orbit Attributes (4)
│   ├── orbitNumber
│   ├── relativeOrbitNumber
│   ├── orbitDirection
│   └── cycleNumber
├── Platform Attributes (3)
│   ├── platformShortName
│   ├── platformSerialIdentifier
│   └── instrumentShortName
├── Processing Attributes (5)
│   ├── processingLevel
│   ├── processingBaseline
│   ├── processingCenter
│   ├── processorName
│   └── processorVersion
├── Product Attributes (5)
│   ├── productType
│   ├── productClass
│   ├── productComposition
│   ├── productConsolidation
│   └── productGeneration
└── Configuration Attributes (3)
    ├── operationalMode
    ├── instrumentConfigurationID
    ├── polarisationChannels
    ├── sliceNumber
    ├── sliceProductFlag
    ├── datatakeID
    └── origin
```

## Data Types and Formats

### Temporal Data
- **ISO 8601 DateTime**: `YYYY-MM-DDTHH:MM:SS.ffffffZ`
- **Precision**: Microsecond precision for timing accuracy
- **Time Zone**: UTC (Z suffix)

### Spatial Data
- **Coordinate System**: WGS84 geographic coordinates
- **Format**: Well-Known Text (WKT) POLYGON
- **Precision**: Decimal degrees with high precision
- **Coverage**: Global extent including polar regions

### Identifiers
- **Orbit Numbers**: Integer values (absolute and relative)
- **Product IDs**: Alphanumeric strings with specific formatting
- **Processing Versions**: Semantic versioning (major.minor format)

### Enumerated Values
- **Platform Names**: Controlled vocabulary (S1A, S1B)
- **Operational Modes**: Fixed set (SM, IW, EW, WV)
- **Orbit Directions**: Binary choice (ASCENDING, DESCENDING)
- **Polarizations**: Standard SAR polarizations (VV, VH, HH, HV)

### 3. Data Types
- **Numerical**: Coordinates, times, measurements
- **Categorical**: Modes, polarizations, directions
- **Temporal**: Timestamps, durations, cycles
- **Spatial**: Coordinates, footprints, orbits

## Key Schema Files

| File | Description | Schema Type |
|------|-------------|-------------|
| `S1_SAR_SLC_attribute_possible_values.csv` | S1 swath attributes | Product Attributes |
| `S2_SAR_SLC_attribute_possible_values.csv` | S2 swath attributes | Product Attributes |
| `S3_SAR_SLC_attribute_possible_values.csv` | S3 swath attributes | Product Attributes |
| `S4_SAR_SLC_attribute_possible_values.csv` | S4 swath attributes | Product Attributes |
| `S5_SAR_SLC_attribute_possible_values.csv` | S5 swath attributes | Product Attributes |
| `S6_SAR_SLC_attribute_possible_values.csv` | S6 swath attributes | Product Attributes |
| `SAR_RAW_SLC_attribute_possible_values.csv` | RAW product attributes | Product Attributes |
| `SAR_SLC_generic_attribute_possible_values.csv` | Generic SLC attributes | Product Attributes |

## Schema Validation

All schemas are validated against:
- **Data Type Constraints**: Ensuring correct data types
- **Value Ranges**: Validating acceptable value ranges
- **Required Fields**: Checking mandatory attributes
- **Format Compliance**: Ensuring standard format adherence

## Common Attributes Across All Schemas

### Core Product Information
- `productType`: Product type identifier (e.g., 'S1_SLC__1S')
- `platformSerialIdentifier`: Satellite identifier ('A' or 'B')
- `processingLevel`: Processing level ('LEVEL0', 'LEVEL1')
- `productClass`: Product class ('S' for Standard)

### Temporal Information
- `startTimeFromAscendingNode`: Start time relative to ascending node
- `completionTimeFromAscendingNode`: Completion time relative to ascending node
- `segmentStartTime`: Segment start timestamp
- `processingDate`: Product processing timestamp

### Spatial Information
- `orbitDirection`: Orbit direction ('ASCENDING', 'DESCENDING')
- `sliceNumber`: Slice number within the product
- `swathIdentifier`: Swath identifier (S1-S6)

### Processing Information
- `processorName`: Processing software name
- `processorVersion`: Processing software version
- `origin`: Data origin ('ESA')

## Schema Evolution

Schemas may evolve over time to accommodate:
- New Sentinel-1 operational modes
- Additional metadata requirements
- Enhanced processing capabilities
- Extended attribute sets

## Validation Rules

### Data Type Validation
```python
# Example validation rules
VALIDATION_RULES = {
    'sliceNumber': {'type': int, 'range': (1, 34)},
    'orbitDirection': {'type': str, 'values': ['ASCENDING', 'DESCENDING']},
    'polarisationChannels': {'type': str, 'values': ['HH', 'VV', 'HH&HV', 'VV&VH']},
    'processingLevel': {'type': str, 'values': ['LEVEL0', 'LEVEL1']}
}
```

### Format Standards
- **Timestamps**: ISO 8601 format (YYYY-MM-DDTHH:MM:SS.sssssssZ)
- **Coordinates**: Decimal degrees
- **Identifiers**: Standard ESA naming conventions
- **Versions**: Semantic versioning (major.minor.patch)

## Related Documentation

- [Sentinel-1 Attributes](sentinel-1-attributes.md) - Detailed attribute specifications
- [Product Types](product-types.md) - Product type definitions
- [Swath Configurations](swath-configurations.md) - Swath-specific schemas
- [API Reference](../api/README.md) - Schema usage in APIs

---

*For technical questions about schema implementation, refer to the source code in `retrieve_attributes.py` and related modules.*
