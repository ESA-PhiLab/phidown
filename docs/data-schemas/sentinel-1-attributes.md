# Sentinel-1 SAR Attributes Reference

This document provides a comprehensive reference for all Sentinel-1 SAR product attributes discovered and cataloged by the SAR project.

## Attribute Categories

### 1. Product Identification
Core attributes that uniquely identify Sentinel-1 products.

#### `productType`
- **Description**: Identifies the type of SAR product
- **Data Type**: String
- **Possible Values**: 
  - `'EW_SLC__1S'` - Extra Wide SLC Level 1
  - `'S2_SLC__1S'` - S2 Swath SLC Level 1
  - `'S1_SLC__1S'` - S1 Swath SLC Level 1
  - `'S4_SLC__1S'` - S4 Swath SLC Level 1
  - `'WV_SLC__1S'` - Wave SLC Level 1
  - `'IW_SLC__1S'` - Interferometric Wide SLC Level 1
  - `'S6_SLC__1S'` - S6 Swath SLC Level 1

#### `platformSerialIdentifier`
- **Description**: Identifies which Sentinel-1 satellite acquired the data
- **Data Type**: String
- **Possible Values**:
  - `'A'` - Sentinel-1A
  - `'B'` - Sentinel-1B

#### `productClass`
- **Description**: Product class designation
- **Data Type**: String
- **Possible Values**: `'S'` (Standard)

### 2. Processing Information

#### `processingLevel`
- **Description**: Level of data processing applied
- **Data Type**: String
- **Possible Values**:
  - `'LEVEL0'` - Raw instrument data
  - `'LEVEL1'` - Single Look Complex (SLC) products

#### `processorName`
- **Description**: Name of the processing software
- **Data Type**: String
- **Possible Values**: `'Sentinel-1 IPF'` (Instrument Processing Facility)

#### `processorVersion`
- **Description**: Version of the processing software
- **Data Type**: String
- **Example Values**: `'003.71'`

#### `processingDate`
- **Description**: Timestamp when the product was processed
- **Data Type**: String (ISO 8601 format)
- **Format**: `YYYY-MM-DDTHH:MM:SS.sssssssZ`
- **Example**: `'2024-05-03T05:31:22.651052Z'`

#### `origin`
- **Description**: Organization responsible for product generation
- **Data Type**: String
- **Possible Values**: `'ESA'` (European Space Agency)

### 3. Acquisition Geometry

#### `orbitDirection`
- **Description**: Direction of satellite orbit during acquisition
- **Data Type**: String
- **Possible Values**:
  - `'ASCENDING'` - Satellite moving from south to north
  - `'DESCENDING'` - Satellite moving from north to south

#### `polarisationChannels`
- **Description**: Radar polarization channels used in acquisition
- **Data Type**: String
- **Possible Values**:
  - `'HH'` - Horizontal transmit, Horizontal receive
  - `'VV'` - Vertical transmit, Vertical receive
  - `'HH&HV'` - Dual polarization: HH and HV
  - `'VV&VH'` - Dual polarization: VV and VH

### 4. Product Structure

#### `sliceNumber`
- **Description**: Sequential number of the slice within the product
- **Data Type**: Integer
- **Range**: 1 to 34
- **Note**: Larger products may be divided into multiple slices

#### `productComposition`
- **Description**: Indicates how the product is composed
- **Data Type**: String
- **Possible Values**:
  - `'Slice'` - Product contains multiple slices
  - `'Individual'` - Single acquisition product

#### `sliceProductFlag`
- **Description**: Boolean flag indicating if this is a slice product
- **Data Type**: Boolean
- **Possible Values**: `False` (typically for full products)

### 5. Temporal Information

#### `segmentStartTime`
- **Description**: Start time of the data acquisition segment
- **Data Type**: String (ISO 8601 format)
- **Format**: `YYYY-MM-DDTHH:MM:SS.sssZ`
- **Example**: `'2024-05-01T15:45:44.732000Z'`

#### `startTimeFromAscendingNode`
- **Description**: Time offset from ascending node crossing to acquisition start
- **Data Type**: Float
- **Units**: Seconds
- **Range**: ~0 to ~6,700,000 seconds

#### `completionTimeFromAscendingNode`
- **Description**: Time offset from ascending node crossing to acquisition completion
- **Data Type**: Float
- **Units**: Seconds
- **Range**: ~0 to ~6,800,000 seconds

## Attribute Validation Rules

### Data Type Constraints
```python
ATTRIBUTE_TYPES = {
    'productType': str,
    'platformSerialIdentifier': str,
    'sliceNumber': int,
    'orbitDirection': str,
    'polarisationChannels': str,
    'processingLevel': str,
    'startTimeFromAscendingNode': float,
    'completionTimeFromAscendingNode': float,
    'segmentStartTime': str,
    'processingDate': str,
    'productClass': str,
    'processorName': str,
    'processorVersion': str,
    'origin': str,
    'productComposition': str,
    'sliceProductFlag': bool
}
```

### Value Constraints
```python
ATTRIBUTE_VALUES = {
    'orbitDirection': ['ASCENDING', 'DESCENDING'],
    'polarisationChannels': ['HH', 'VV', 'HH&HV', 'VV&VH'],
    'processingLevel': ['LEVEL0', 'LEVEL1'],
    'platformSerialIdentifier': ['A', 'B'],
    'productClass': ['S'],
    'origin': ['ESA'],
    'productComposition': ['Slice', 'Individual']
}
```

## Usage Examples

### Filtering by Attributes
```python
# Filter products by orbit direction
ascending_products = df[df['orbitDirection'] == 'ASCENDING']

# Filter by polarization
dual_pol_products = df[df['polarisationChannels'].isin(['HH&HV', 'VV&VH'])]

# Filter by processing level
slc_products = df[df['processingLevel'] == 'LEVEL1']
```

### Attribute Analysis
```python
# Analyze distribution of orbit directions
orbit_distribution = df['orbitDirection'].value_counts()

# Check polarization usage
polarization_stats = df['polarisationChannels'].value_counts()

# Temporal analysis
df['processingDate'] = pd.to_datetime(df['processingDate'])
daily_processing = df.groupby(df['processingDate'].dt.date).size()
```

## Related Documentation

- [Data Schemas Overview](README.md) - Schema documentation overview
- [Product Types](product-types.md) - Detailed product type specifications
- [Swath Configurations](swath-configurations.md) - Swath-specific attribute details
- [S1 Swath Attributes](../attributes/s1-attributes.md) - S1 specific attributes

---

*This reference is automatically generated from discovered product attributes. For the most current attribute values, refer to the CSV files in the project root.*
