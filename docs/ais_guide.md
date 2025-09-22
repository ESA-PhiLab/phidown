# AIS Data Handler

The AIS (Automatic Identification System) module provides functionality to download, filter, and process AIS data from Hugging Face datasets.

## Installation

The AIS functionality requires additional dependencies:

```bash
# Install with AIS support
pip install phidown[ais]

# Or install dependencies manually
pip install huggingface_hub shapely
```

## Quick Start

### Basic Usage

```python
from phidown.ais import download_ais_data

# Download AIS data for a single day
df = download_ais_data("2025-08-25")
print(f"Downloaded {len(df)} AIS records")
```

### Time Filtering

```python
# Download with time window (10:00 to 12:00 UTC)
df = download_ais_data(
    start_date="2025-08-25",
    start_time="10:00:00",
    end_time="12:00:00"
)
```

### Spatial Filtering with AOI

```python
# Define Area of Interest (AOI) as WKT polygon
aoi_wkt = """POLYGON((4.2100 51.3700,4.4800 51.3700,4.5100 51.2900,
             4.4650 51.1700,4.2500 51.1700,4.1900 51.2500,4.2100 51.3700))"""

df = download_ais_data(
    start_date="2025-08-25", 
    aoi_wkt=aoi_wkt
)
```

## Advanced Usage

### Using the AISDataHandler Class

```python
from datetime import date, time
from phidown.ais import AISDataHandler

# Create handler instance
handler = AISDataHandler()

# Download data with all filters
df = handler.get_ais_data(
    start_date=date(2025, 8, 25),
    end_date=date(2025, 8, 26),
    start_time=time(9, 0, 0),
    end_time=time(15, 0, 0),
    aoi_wkt="POLYGON((4.0 51.0,5.0 51.0,5.0 52.0,4.0 52.0,4.0 51.0))"
)

# Check for errors during processing
errors = handler.get_errors()
if errors:
    print("Encountered errors:")
    for error in errors:
        print(f"  - {error}")
```

### Custom Hugging Face Repository

```python
# Use custom repository
handler = AISDataHandler(
    hf_repo_id="your-org/custom-ais-repo",
    file_template="ais_data_{date}.parquet"
)

df = handler.get_ais_data("2025-08-25")
```

## Data Format

The returned DataFrame contains the following standardized columns:

- `name`: Vessel name (string)
- `lat`: Latitude (float)
- `lon`: Longitude (float)  
- `source_date`: Date of data source (YYYY-MM-DD string)
- `timestamp`: Timestamp in YYYY-MM-DD HH:MM:SS format (string)
- `mmsi`: Maritime Mobile Service Identity (string)

## Error Handling

The AIS handler gracefully handles various error conditions:

- Missing data files for requested dates
- Corrupted or unreadable parquet files
- Missing coordinate or timestamp columns
- Invalid WKT geometry for AOI filtering

Errors are collected and can be retrieved using the `get_errors()` method.

## Time Window Filtering

Time filtering supports:

- **Normal time windows**: e.g., 10:00 to 14:00
- **Overnight windows**: e.g., 22:00 to 06:00 (crosses midnight)
- **Start time only**: filters from start time to end of day
- **End time only**: filters from start of day to end time

Time formats supported:

- `HH:MM:SS` (e.g., "14:30:45")
- `HH:MM` (e.g., "14:30")

## Spatial Filtering

AOI filtering requires the `shapely` library and accepts:

- WKT (Well-Known Text) polygon strings
- Any valid polygon geometry
- Points on polygon boundaries are included

Example WKT polygons:

```python
# Simple rectangle
aoi = "POLYGON((4.0 51.0,5.0 51.0,5.0 52.0,4.0 52.0,4.0 51.0))"

# Complex polygon around Netherlands coast
aoi = """POLYGON((4.2100 51.3700,4.4800 51.3700,4.5100 51.2900,
         4.4650 51.1700,4.2500 51.1700,4.1900 51.2500,4.2100 51.3700))"""
```

## Dependencies

- **Required**: `pandas`, `huggingface_hub`
- **Optional**: `shapely` (for AOI filtering)

## Performance Notes

- Data is downloaded once per date and cached locally by Hugging Face Hub
- Large datasets are processed incrementally to manage memory usage
- Spatial filtering is performed in-memory and may be slow for large datasets
- Consider using time filtering to reduce data volume before spatial filtering
