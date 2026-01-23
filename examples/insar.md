
# InSAR Data Acquisition Script

Automated Sentinel-1 SLC and Burst download for InSAR processing.

## Quick Start

```bash
# 1. Create a config file
python insar.py --create-config

# 2. Edit insar_config.yaml with your AOI and dates

# 3. Search and download
python insar.py insar_config.yaml --download
```

## Usage

```bash
python insar.py config.yaml                  # Search and show results
python insar.py config.yaml --dry-run        # Search without downloading
python insar.py config.yaml --find-optimal   # Find optimal orbit for AOI
python insar.py config.yaml --download       # Search and download data
python insar.py --create-config              # Create sample config file
```

## Configuration File

Minimal `config.yaml` example:

```yaml
search:
  aoi_wkt: "POLYGON((12.4 41.8, 12.6 41.8, 12.6 42.0, 12.4 42.0, 12.4 41.8))"
  start_date: "2024-08-01T00:00:00"
  end_date: "2024-09-30T00:00:00"
  mode: slc              # 'slc' or 'burst'
  polarisation: VV       # VV, VH, HH, HV
  orbit_direction: null  # null = auto-detect, or ASCENDING/DESCENDING
  relative_orbit: null   # null = auto-detect, or 1-175
  platforms: [all]       # [all], [A], [B], [A, B], etc.

download:
  output_dir: ./data
  username: null         # or set CDSE_USERNAME env var
  password: null         # or set CDSE_PASSWORD env var
  retry_count: 3
```

## Key Features

| Feature | Description |
|---------|-------------|
| **Auto orbit detection** | Finds orbit/track maximizing AOI coverage |
| **Burst mode** | Download individual bursts (IW1 preferred) |
| **Platform filter** | Select S1A, S1B, S1C, S1D or combinations |
| **Retry logic** | Auto-retry failed downloads |
| **Resume** | Skip already downloaded products |
| **Statistics** | Temporal gap analysis + distribution plot |

## Outputs

- `statistics/search_results.csv` — All found products
- `statistics/temporal_statistics.json` — Acquisition gap stats
- `statistics/temporal_distribution.png` — Temporal plot
- `data/` — Downloaded products

## Credentials

For burst downloads, set CDSE credentials:

```bash
export CDSE_USERNAME="your_email"
export CDSE_PASSWORD="your_password"
```

Or add them to the config file.