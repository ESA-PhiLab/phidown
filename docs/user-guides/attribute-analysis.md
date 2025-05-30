# SAR Attribute Analysis User Guide

## Introduction

This guide provides step-by-step instructions for analyzing Sentinel-1 SAR SLC product attributes. Based on comprehensive analysis of Sentinel-1 data spanning 2019-2024, this guide will help you understand, query, and utilize SAR product metadata effectively.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Understanding SAR Attributes](#understanding-sar-attributes)
3. [Temporal Analysis](#temporal-analysis)
4. [Spatial Analysis](#spatial-analysis)
5. [Orbit Analysis](#orbit-analysis)
6. [Quality Assessment](#quality-assessment)
7. [Advanced Queries](#advanced-queries)
8. [Best Practices](#best-practices)

## Getting Started

### Prerequisites
- Basic understanding of SAR principles
- Familiarity with geographic coordinate systems
- Knowledge of ISO 8601 datetime formats

### Required Data
- Access to Sentinel-1 SLC attribute database
- CSV file with attribute data (`S1_SAR_SLC_attribute_possible_values.csv`)

### Initial Setup
```python
import pandas as pd
import geopandas as gpd
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

# Load attribute data
attributes_df = pd.read_csv('S1_SAR_SLC_attribute_possible_values.csv')
print(f"Loaded {len(attributes_df)} attribute records")
```

## Understanding SAR Attributes

### Core Attribute Categories

#### 1. Temporal Attributes
Essential for time-series analysis and temporal filtering:

```python
# Parse datetime columns
datetime_cols = ['beginningDateTime', 'endingDateTime', 'processingDate']
for col in datetime_cols:
    if col in attributes_df.columns:
        attributes_df[col] = pd.to_datetime(attributes_df[col])

# Calculate acquisition duration
if 'beginningDateTime' in attributes_df.columns and 'endingDateTime' in attributes_df.columns:
    attributes_df['acquisition_duration'] = (
        attributes_df['endingDateTime'] - attributes_df['beginningDateTime']
    ).dt.total_seconds()
```

#### 2. Spatial Attributes
For geographic analysis and spatial filtering:

```python
# Parse WKT coordinates if available
from shapely.wkt import loads
if 'coordinates' in attributes_df.columns:
    # Extract sample coordinate for analysis
    sample_coords = attributes_df['coordinates'].iloc[0]
    print(f"Sample coordinates: {sample_coords}")
    
    # Convert to geometry if needed
    # geometries = attributes_df['coordinates'].apply(loads)
```

#### 3. Platform and Orbit Attributes
For mission planning and interferometric analysis:

```python
# Analyze platform distribution
if 'platformShortName' in attributes_df.columns:
    platform_counts = attributes_df['platformShortName'].value_counts()
    print("Platform distribution:")
    print(platform_counts)

# Orbit analysis
if 'orbitDirection' in attributes_df.columns:
    orbit_direction_counts = attributes_df['orbitDirection'].value_counts()
    print("\\nOrbit direction distribution:")
    print(orbit_direction_counts)
```

## Temporal Analysis

### Time Series Exploration

#### Acquisition Timeline
```python
# Plot acquisition timeline
if 'beginningDateTime' in attributes_df.columns:
    # Group by date
    daily_counts = attributes_df.groupby(
        attributes_df['beginningDateTime'].dt.date
    ).size()
    
    # Plot timeline
    plt.figure(figsize=(12, 6))
    daily_counts.plot(kind='line')
    plt.title('Sentinel-1 SLC Acquisitions Over Time')
    plt.xlabel('Date')
    plt.ylabel('Number of Acquisitions')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()
```

#### Seasonal Patterns
```python
# Analyze seasonal acquisition patterns
if 'beginningDateTime' in attributes_df.columns:
    attributes_df['month'] = attributes_df['beginningDateTime'].dt.month
    attributes_df['year'] = attributes_df['beginningDateTime'].dt.year
    
    # Monthly distribution
    monthly_counts = attributes_df['month'].value_counts().sort_index()
    
    plt.figure(figsize=(10, 6))
    monthly_counts.plot(kind='bar')
    plt.title('Acquisitions by Month')
    plt.xlabel('Month')
    plt.ylabel('Count')
    plt.xticks(range(12), ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                          'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'])
    plt.show()
```

### Processing Lag Analysis
```python
# Calculate processing lag
if 'beginningDateTime' in attributes_df.columns and 'processingDate' in attributes_df.columns:
    attributes_df['processing_lag'] = (
        attributes_df['processingDate'] - attributes_df['beginningDateTime']
    ).dt.total_seconds() / 3600  # Convert to hours
    
    # Plot processing lag distribution
    plt.figure(figsize=(10, 6))
    attributes_df['processing_lag'].hist(bins=50, alpha=0.7)
    plt.title('Processing Lag Distribution')
    plt.xlabel('Processing Lag (hours)')
    plt.ylabel('Frequency')
    plt.show()
    
    print(f"Median processing lag: {attributes_df['processing_lag'].median():.1f} hours")
```

## Spatial Analysis

### Geographic Coverage Assessment
```python
# Analyze coordinate bounds (if coordinates are available)
def analyze_spatial_coverage(df):
    \"\"\"Analyze spatial coverage from coordinate data\"\"\"
    if 'coordinates' not in df.columns:
        print("No coordinate data available")
        return
    
    print("Spatial Coverage Analysis:")
    print("=" * 40)
    
    # Sample analysis of coordinate patterns
    coord_sample = df['coordinates'].dropna().head(10)
    print(f"Sample coordinates (first 10):")
    for i, coord in enumerate(coord_sample):
        print(f"{i+1}. {coord[:100]}...")

analyze_spatial_coverage(attributes_df)
```

### Regional Distribution
```python
# If coordinate parsing is available
def extract_coordinate_bounds(wkt_polygon):
    \"\"\"Extract min/max lat/lon from WKT polygon\"\"\"
    try:
        from shapely.wkt import loads
        geom = loads(wkt_polygon)
        bounds = geom.bounds  # (minx, miny, maxx, maxy)
        return {
            'min_lon': bounds[0], 'min_lat': bounds[1],
            'max_lon': bounds[2], 'max_lat': bounds[3]
        }
    except:
        return None

# Apply to sample of data if coordinates available
if 'coordinates' in attributes_df.columns:
    print("Coordinate analysis requires shapely library for full implementation")
    print("Sample coordinate format check:")
    sample_coord = attributes_df['coordinates'].iloc[0] if len(attributes_df) > 0 else None
    if sample_coord:
        print(f"Sample: {sample_coord[:200]}...")
```

## Orbit Analysis

### Orbit Pattern Analysis
```python
# Analyze orbit characteristics
def analyze_orbits(df):
    \"\"\"Comprehensive orbit analysis\"\"\"
    print("Orbit Analysis:")
    print("=" * 30)
    
    # Relative orbit distribution
    if 'relativeOrbitNumber' in df.columns:
        rel_orbit_stats = df['relativeOrbitNumber'].describe()
        print("Relative Orbit Statistics:")
        print(rel_orbit_stats)
        
        # Plot relative orbit distribution
        plt.figure(figsize=(12, 6))
        df['relativeOrbitNumber'].hist(bins=50, alpha=0.7, edgecolor='black')
        plt.title('Relative Orbit Number Distribution')
        plt.xlabel('Relative Orbit Number')
        plt.ylabel('Frequency')
        plt.grid(True, alpha=0.3)
        plt.show()
    
    # Orbit direction analysis
    if 'orbitDirection' in df.columns:
        direction_counts = df['orbitDirection'].value_counts()
        print("\\nOrbit Direction Distribution:")
        print(direction_counts)
        
        plt.figure(figsize=(8, 6))
        direction_counts.plot(kind='pie', autopct='%1.1f%%')
        plt.title('Orbit Direction Distribution')
        plt.ylabel('')
        plt.show()

analyze_orbits(attributes_df)
```

### Cycle Analysis
```python
# Analyze orbit cycles
if 'cycleNumber' in attributes_df.columns:
    cycle_stats = attributes_df['cycleNumber'].describe()
    print("Cycle Number Statistics:")
    print(cycle_stats)
    
    # Plot cycle progression over time
    if 'beginningDateTime' in attributes_df.columns:
        plt.figure(figsize=(12, 6))
        plt.scatter(attributes_df['beginningDateTime'], 
                   attributes_df['cycleNumber'], 
                   alpha=0.6, s=1)
        plt.title('Cycle Number vs Acquisition Time')
        plt.xlabel('Acquisition Date')
        plt.ylabel('Cycle Number')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.show()
```

## Quality Assessment

### Processing Quality Analysis
```python
def analyze_processing_quality(df):
    \"\"\"Analyze processing-related attributes\"\"\"
    print("Processing Quality Analysis:")
    print("=" * 35)
    
    # Processing baseline distribution
    if 'processingBaseline' in df.columns:
        baseline_counts = df['processingBaseline'].value_counts()
        print("Processing Baseline Distribution:")
        print(baseline_counts.head(10))
        
        plt.figure(figsize=(10, 6))
        baseline_counts.head(10).plot(kind='bar')
        plt.title('Top 10 Processing Baselines')
        plt.xlabel('Processing Baseline')
        plt.ylabel('Count')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.show()
    
    # Processing center analysis
    if 'processingCenter' in df.columns:
        center_counts = df['processingCenter'].value_counts()
        print("\\nProcessing Center Distribution:")
        print(center_counts)
    
    # Processor version analysis
    if 'processorVersion' in df.columns:
        version_counts = df['processorVersion'].value_counts()
        print("\\nProcessor Version Distribution:")
        print(version_counts.head(10))

analyze_processing_quality(attributes_df)
```

### Data Completeness Assessment
```python
def assess_data_completeness(df):
    \"\"\"Assess completeness of attribute data\"\"\"
    print("Data Completeness Assessment:")
    print("=" * 40)
    
    total_records = len(df)
    print(f"Total records: {total_records}")
    
    completeness = {}
    for column in df.columns:
        non_null_count = df[column].notna().sum()
        completeness[column] = (non_null_count / total_records) * 100
    
    # Sort by completeness
    completeness_df = pd.DataFrame(list(completeness.items()), 
                                 columns=['Attribute', 'Completeness_Percent'])
    completeness_df = completeness_df.sort_values('Completeness_Percent', ascending=False)
    
    print("\\nAttribute Completeness:")
    print(completeness_df.to_string(index=False))
    
    # Plot completeness
    plt.figure(figsize=(12, 8))
    plt.barh(completeness_df['Attribute'], completeness_df['Completeness_Percent'])
    plt.title('Attribute Data Completeness')
    plt.xlabel('Completeness (%)')
    plt.ylabel('Attributes')
    plt.gca().invert_yaxis()
    plt.tight_layout()
    plt.show()
    
    return completeness_df

completeness_results = assess_data_completeness(attributes_df)
```

## Advanced Queries

### Complex Filtering Examples

#### Multi-criteria Search
```python
def advanced_search(df, criteria):
    \"\"\"Perform advanced multi-criteria search\"\"\"
    result = df.copy()
    
    # Temporal filtering
    if 'start_date' in criteria and 'beginningDateTime' in df.columns:
        result = result[result['beginningDateTime'] >= criteria['start_date']]
    
    if 'end_date' in criteria and 'endingDateTime' in df.columns:
        result = result[result['endingDateTime'] <= criteria['end_date']]
    
    # Platform filtering
    if 'platforms' in criteria and 'platformShortName' in df.columns:
        result = result[result['platformShortName'].isin(criteria['platforms'])]
    
    # Orbit filtering
    if 'orbit_direction' in criteria and 'orbitDirection' in df.columns:
        result = result[result['orbitDirection'] == criteria['orbit_direction']]
    
    # Mode filtering
    if 'operational_modes' in criteria and 'operationalMode' in df.columns:
        result = result[result['operationalMode'].isin(criteria['operational_modes'])]
    
    return result

# Example search
search_criteria = {
    'start_date': '2023-01-01',
    'end_date': '2023-12-31',
    'platforms': ['S1A', 'S1B'],
    'orbit_direction': 'ASCENDING',
    'operational_modes': ['IW']
}

# filtered_results = advanced_search(attributes_df, search_criteria)
# print(f"Found {len(filtered_results)} matching products")
```

#### Interferometric Pair Identification
```python
def find_interferometric_pairs(df, max_temporal_baseline=12):
    \"\"\"Find potential interferometric pairs\"\"\"
    if 'relativeOrbitNumber' not in df.columns or 'beginningDateTime' not in df.columns:
        print("Required attributes not available for interferometric analysis")
        return None
    
    pairs = []
    
    # Group by relative orbit and orbit direction
    groups = df.groupby(['relativeOrbitNumber', 'orbitDirection'])
    
    for (rel_orbit, direction), group in groups:
        if len(group) < 2:
            continue
            
        # Sort by acquisition time
        group_sorted = group.sort_values('beginningDateTime')
        
        # Find pairs within temporal baseline
        for i in range(len(group_sorted)):
            for j in range(i+1, len(group_sorted)):
                time_diff = (group_sorted.iloc[j]['beginningDateTime'] - 
                           group_sorted.iloc[i]['beginningDateTime']).days
                
                if time_diff <= max_temporal_baseline:
                    pairs.append({
                        'master_date': group_sorted.iloc[i]['beginningDateTime'],
                        'slave_date': group_sorted.iloc[j]['beginningDateTime'],
                        'temporal_baseline': time_diff,
                        'relative_orbit': rel_orbit,
                        'orbit_direction': direction
                    })
    
    return pd.DataFrame(pairs)

# pairs_df = find_interferometric_pairs(attributes_df)
# if pairs_df is not None:
#     print(f"Found {len(pairs_df)} potential interferometric pairs")
```

## Best Practices

### 1. Data Validation
```python
def validate_attributes(df):
    \"\"\"Validate attribute data quality\"\"\"
    issues = []
    
    # Check datetime consistency
    if 'beginningDateTime' in df.columns and 'endingDateTime' in df.columns:
        invalid_times = df[df['beginningDateTime'] >= df['endingDateTime']]
        if len(invalid_times) > 0:
            issues.append(f"Found {len(invalid_times)} records with invalid time ranges")
    
    # Check orbit number ranges
    if 'relativeOrbitNumber' in df.columns:
        invalid_orbits = df[(df['relativeOrbitNumber'] < 1) | 
                           (df['relativeOrbitNumber'] > 175)]
        if len(invalid_orbits) > 0:
            issues.append(f"Found {len(invalid_orbits)} records with invalid relative orbit numbers")
    
    # Check for required fields
    required_fields = ['platformShortName', 'operationalMode']
    for field in required_fields:
        if field in df.columns:
            missing = df[field].isna().sum()
            if missing > 0:
                issues.append(f"Field '{field}' has {missing} missing values")
    
    return issues

validation_issues = validate_attributes(attributes_df)
if validation_issues:
    print("Data validation issues found:")
    for issue in validation_issues:
        print(f"- {issue}")
else:
    print("Data validation passed!")
```

### 2. Performance Optimization
```python
# Index commonly queried columns
def optimize_dataframe(df):
    \"\"\"Optimize dataframe for common queries\"\"\"
    optimized_df = df.copy()
    
    # Convert datetime columns
    datetime_cols = ['beginningDateTime', 'endingDateTime', 'processingDate']
    for col in datetime_cols:
        if col in optimized_df.columns:
            optimized_df[col] = pd.to_datetime(optimized_df[col])
    
    # Convert categorical columns
    categorical_cols = ['platformShortName', 'orbitDirection', 'operationalMode']
    for col in categorical_cols:
        if col in optimized_df.columns:
            optimized_df[col] = optimized_df[col].astype('category')
    
    return optimized_df

# optimized_attributes = optimize_dataframe(attributes_df)
```

### 3. Memory Management
```python
# For large datasets, process in chunks
def process_large_dataset(file_path, chunk_size=10000):
    \"\"\"Process large attribute datasets in chunks\"\"\"
    chunk_results = []
    
    for chunk in pd.read_csv(file_path, chunksize=chunk_size):
        # Process each chunk
        processed_chunk = process_attributes_chunk(chunk)
        chunk_results.append(processed_chunk)
    
    return pd.concat(chunk_results, ignore_index=True)

def process_attributes_chunk(chunk):
    \"\"\"Process a single chunk of attribute data\"\"\"
    # Apply necessary transformations
    if 'beginningDateTime' in chunk.columns:
        chunk['beginningDateTime'] = pd.to_datetime(chunk['beginningDateTime'])
    
    return chunk
```

## Summary

This guide provides comprehensive methods for analyzing SAR attribute data. Key takeaways:

1. **Always validate data** before analysis
2. **Use appropriate data types** for efficient processing
3. **Consider temporal and spatial patterns** in your analysis
4. **Leverage orbit characteristics** for interferometric applications
5. **Monitor processing quality** indicators
6. **Optimize performance** for large datasets

## Related Documentation

- [Sentinel-1 Attributes Reference](../attributes/sentinel-1-attributes-reference.md)
- [Data Schemas Overview](../data-schemas/README.md)
- [API Documentation](../api/README.md)
- [Processing Workflows](processing-workflows.md)
