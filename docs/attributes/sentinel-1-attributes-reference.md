# Sentinel-1 SAR SLC Attributes Reference

## Overview

This document provides a comprehensive reference for all Sentinel-1 SAR Single Look Complex (SLC) product attributes. Based on analysis of actual Sentinel-1 data spanning 2019-2024, this reference includes detailed descriptions, possible values, and usage guidelines for each attribute.

## Table of Contents

1. [Temporal Attributes](#temporal-attributes)
2. [Spatial Attributes](#spatial-attributes)
3. [Orbit Attributes](#orbit-attributes)
4. [Platform Attributes](#platform-attributes)
5. [Processing Attributes](#processing-attributes)
6. [Product Attributes](#product-attributes)
7. [Configuration Attributes](#configuration-attributes)

---

## Temporal Attributes

### beginningDateTime
**Description**: Start time of data acquisition  
**Format**: ISO 8601 datetime  
**Example Values**: 
- `2019-01-01T05:16:02.123456Z`
- `2024-12-31T23:45:30.987654Z`  
**Usage**: Defines the beginning of the imaging interval for the SAR acquisition

### endingDateTime
**Description**: End time of data acquisition  
**Format**: ISO 8601 datetime  
**Example Values**:
- `2019-01-01T05:16:15.456789Z`
- `2024-12-31T23:45:43.321098Z`  
**Usage**: Defines the end of the imaging interval for the SAR acquisition

### completionTimeFromAscendingNode
**Description**: Time elapsed from ascending node crossing to acquisition completion  
**Format**: Decimal seconds  
**Range**: 0.0 - 6000.0 seconds  
**Usage**: Orbital timing reference for precise geolocation

### segmentStartTime
**Description**: Start time of the specific data segment  
**Format**: ISO 8601 datetime  
**Usage**: For products divided into segments, defines segment timing

### processingDate
**Description**: Date when the product was processed  
**Format**: ISO 8601 datetime  
**Usage**: Quality control and version tracking

---

## Spatial Attributes

### coordinates
**Description**: Geographic bounding box coordinates  
**Format**: Well-Known Text (WKT) POLYGON  
**Example**: `POLYGON((-180 -90, 180 -90, 180 90, -180 90, -180 -90))`  
**Coverage**: Global coverage including polar regions  
**Usage**: Spatial filtering and geographic reference

---

## Orbit Attributes

### orbitNumber
**Description**: Absolute orbit number  
**Format**: Integer  
**Range**: 1 - 60000+  
**Usage**: Unique identifier for each orbital pass

### relativeOrbitNumber
**Description**: Relative orbit number within repeat cycle  
**Format**: Integer  
**Range**: 1 - 175  
**Usage**: Interferometric processing and repeat-pass analysis

### orbitDirection
**Description**: Satellite flight direction  
**Possible Values**:
- `ASCENDING`: Northward flight
- `DESCENDING`: Southward flight  
**Usage**: Geometric corrections and look angle calculations

### cycleNumber
**Description**: Orbit repeat cycle number  
**Format**: Integer  
**Range**: 1 - 300+  
**Usage**: Long-term time series analysis

---

## Platform Attributes

### platformShortName
**Description**: Satellite platform identifier  
**Possible Values**:
- `S1A`: Sentinel-1A
- `S1B`: Sentinel-1B  
**Usage**: Multi-platform analysis and mission planning

### platformSerialIdentifier
**Description**: Unique platform serial number  
**Format**: Alphanumeric string  
**Usage**: Platform-specific calibration and processing

### instrumentShortName
**Description**: Instrument identifier  
**Value**: `SAR-C`  
**Usage**: C-band SAR instrument identification

---

## Processing Attributes

### processingLevel
**Description**: Data processing level  
**Value**: `L1` (Level 1 - SLC products)  
**Usage**: Processing chain identification

### processingBaseline
**Description**: Processing software baseline version  
**Format**: Numeric version (e.g., `003.40`, `003.52`)  
**Usage**: Algorithm version tracking and quality assessment

### processingCenter
**Description**: Facility where processing occurred  
**Common Values**:
- `ESA`: European Space Agency
- `CGS`: Copernicus Ground Segment  
**Usage**: Processing quality and methodology reference

### processorName
**Description**: Processing software name  
**Value**: Typically IPF (Instrument Processing Facility)  
**Usage**: Software identification and version control

### processorVersion
**Description**: Detailed processor version  
**Format**: Version string (e.g., `03.40`, `03.52`)  
**Usage**: Precise algorithm version tracking

---

## Product Attributes

### productType
**Description**: Product type specification  
**Value**: `RAW` or `SLC`  
**Usage**: Product identification and processing level

### productClass
**Description**: Product classification  
**Possible Values**:
- `S`: Standard product
- `A`: Annotation product  
**Usage**: Product category identification

### productComposition
**Description**: Product data composition  
**Common Values**:
- `Individual`: Single acquisition
- `Slice`: Data slice  
**Usage**: Product assembly information

### productConsolidation
**Description**: Product consolidation status  
**Values**: Various consolidation states  
**Usage**: Product completeness verification

### productGeneration
**Description**: Product generation methodology  
**Usage**: Processing approach identification

---

## Configuration Attributes

### operationalMode
**Description**: SAR acquisition mode  
**Possible Values**:
- `SM`: Strip Map
- `IW`: Interferometric Wide swath
- `EW`: Extra Wide swath
- `WV`: Wave mode  
**Usage**: Acquisition geometry and resolution characteristics

### instrumentConfigurationID
**Description**: Instrument configuration identifier  
**Format**: Numeric ID  
**Usage**: Acquisition parameter sets

### polarisationChannels
**Description**: Radar polarization channels  
**Common Values**:
- `VV`: Vertical transmit, Vertical receive
- `VH`: Vertical transmit, Horizontal receive
- `HH`: Horizontal transmit, Horizontal receive
- `HV`: Horizontal transmit, Vertical receive  
**Usage**: Polarimetric analysis and target characterization

### sliceNumber
**Description**: Data slice identifier  
**Format**: Integer  
**Usage**: Product segmentation tracking

### sliceProductFlag
**Description**: Indicates if product is a slice  
**Values**: Boolean or flag indicator  
**Usage**: Product type verification

### datatakeID
**Description**: Unique identifier for data acquisition  
**Format**: Hexadecimal string  
**Usage**: Raw data traceability

### origin
**Description**: Data origin or source  
**Usage**: Data provenance tracking

---

## Data Quality and Validation

### Temporal Coverage
- **Start Date**: 2019 (earliest observed)
- **End Date**: 2024 (latest observed)
- **Completeness**: Continuous coverage with regular acquisitions

### Spatial Coverage
- **Global**: All latitudes and longitudes
- **Polar Regions**: Included in coverage
- **Ocean/Land**: Both domains covered

### Processing Quality
- Multiple processing baselines ensure algorithm evolution
- Consistent processor versions indicate stable processing
- ESA processing centers ensure quality standards

---

## Usage Examples

### Temporal Filtering
```python
# Filter by acquisition date range
start_date = "2023-01-01T00:00:00Z"
end_date = "2023-12-31T23:59:59Z"
products = filter_by_date_range(beginningDateTime, start_date, end_date)
```

### Spatial Filtering
```python
# Filter by geographic region
bbox = "POLYGON((0 40, 10 40, 10 50, 0 50, 0 40))"
products = filter_by_coordinates(coordinates, bbox)
```

### Orbit Analysis
```python
# Group by relative orbit for interferometry
relative_orbits = group_by(relativeOrbitNumber)
ascending_passes = filter_by(orbitDirection, "ASCENDING")
```

## Related Documentation

- [Data Schemas Overview](../data-schemas/README.md)
- [Search API Reference](../api/search-api.md)
- [Attribute Analysis Guide](../user-guides/attribute-analysis.md)
- [Processing Workflows](../user-guides/processing-workflows.md)
