![Phi-Down Logo](./assets/banner_phidown.svg)

[![PyPI](https://img.shields.io/pypi/v/phidown.svg)](https://pypi.org/project/phidown/)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![Docs](https://img.shields.io/badge/docs-online-blue.svg)](https://esa-philab.github.io/phidown)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.15332053.svg)](https://doi.org/10.5281/zenodo.15332053)

# phidown

`phidown` is a Python package and CLI for searching and downloading Copernicus Data Space products.

It supports:
- Product search with OData filters (collection, dates, AOI, orbit direction, cloud cover).
- Product download through S3 (`s5cmd`).
- Sentinel-1 SLC burst search and burst coverage analysis workflows.

## Installation

### From PyPI

```bash
pip install phidown
```

### Optional dependency groups

```bash
# Visualization and mapping tools
pip install "phidown[viz]"

# AIS-related utilities
pip install "phidown[ais]"

# Jupyter environment helpers
pip install "phidown[jupyter_env]"

# Development and docs
pip install "phidown[dev,docs]"
```

### From source (PDM)

```bash
git clone https://github.com/ESA-PhiLab/phidown.git
cd phidown
pdm install
```

Requirements:
- Python 3.9+
- `s5cmd` available on your `PATH` for S3 downloads

## Credentials

To download from CDSE S3, create a `.s5cfg` file:

```ini
[default]
aws_access_key_id = your_access_key
aws_secret_access_key = your_secret_key
aws_region = eu-central-1
host_base = eodata.dataspace.copernicus.eu
host_bucket = eodata.dataspace.copernicus.eu
use_https = true
check_ssl_certificate = true
```

If credentials are not removed automatically, revoke them in the CDSE S3 Credentials Manager:
<https://eodata-s3keysmanager.dataspace.copernicus.eu/panel/s3-credentials>

## Quick Start (Python API)

```python
from phidown.search import CopernicusDataSearcher

searcher = CopernicusDataSearcher()
searcher.query_by_filter(
    collection_name="SENTINEL-1",
    product_type="SLC",
    start_date="2024-05-01T00:00:00",
    end_date="2024-05-31T23:59:59",
    top=50,
)

df = searcher.execute_query()
print(f"Results: {len(df)}")
print(searcher.display_results(top_n=5))
```

### Sentinel-1 burst mode

```python
from phidown.search import CopernicusDataSearcher

searcher = CopernicusDataSearcher()
searcher.query_by_filter(
    burst_mode=True,
    swath_identifier="IW2",
    polarisation_channels="VV",
    orbit_direction="DESCENDING",
    start_date="2024-08-02T00:00:00",
    end_date="2024-08-15T00:00:00",
    top=20,
    count=True,
)

df = searcher.execute_query()
print(f"Bursts found: {len(df)}")
```

## Command Line Interface

Show available options:

```bash
phidown --help
```

Common commands:

```bash
# Download by product name
phidown --name S1A_IW_GRDH_1SDV_20141031T161924_20141031T161949_003076_003856_634E.SAFE -o ./data

# Download by S3 path
phidown --s3path /eodata/Sentinel-1/SAR/IW_GRDH_1S/2024/05/03/... -o ./data

# List products for AOI/date filters
phidown --list --collection SENTINEL-1 --product-type GRD --bbox -5 40 5 45 --start-date 2024-01-01T00:00:00 --end-date 2024-01-31T23:59:59

# Burst coverage analysis
phidown --burst-coverage --bbox -5 40 5 45 --start-date 2024-08-02T00:00:00 --end-date 2024-08-15T23:59:59 --polarisation VV --format json
```

## Documentation

Full documentation: <https://esa-philab.github.io/phidown>

Useful entry points:
- Getting started: <https://esa-philab.github.io/phidown/getting_started.html>
- User guide: <https://esa-philab.github.io/phidown/user_guide.html>
- API reference: <https://esa-philab.github.io/phidown/api_reference.html>
- Burst mode guide: <https://esa-philab.github.io/phidown/sentinel1_burst_mode.html>

Notebook examples:
- `./how_to_start.ipynb`
- `./notebooks/`

## Contributing

Contributions are welcome. See `CONTRIBUTING.md` for development setup,
validation commands, and pull request expectations.

For bugs and questions, use:
- Issues: <https://github.com/ESA-PhiLab/phidown/issues>
- Discussions: <https://github.com/ESA-PhiLab/phidown/discussions>

## Citation

If you use `phidown` in research, please cite it using the metadata in
`CITATION.cff` or the Zenodo record below:

> Del Prete, R. (2025). *phidown: A Python Tool for Streamlined Data Downloading from CDSE*. Zenodo. <https://doi.org/10.5281/zenodo.15332053>

BibTeX:

```bibtex
@misc{delprete2025phidown,
  author    = {Del Prete, Roberto},
  title     = {phidown: A Python Tool for Streamlined Data Downloading from CDSE},
  year      = {2025},
  publisher = {Zenodo},
  doi       = {10.5281/zenodo.15332053},
  url       = {https://doi.org/10.5281/zenodo.15332053}
}
```

## License

This project is licensed under the Apache License 2.0.
See `LICENSE` for details.
