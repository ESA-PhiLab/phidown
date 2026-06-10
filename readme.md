![Phi-Down Logo](./assets/banner.png)

[![PyPI](https://img.shields.io/pypi/v/phidown.svg)](https://pypi.org/project/phidown/)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![Docs](https://img.shields.io/badge/docs-online-blue.svg)](https://esa-philab.github.io/phidown)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.15332053.svg)](https://doi.org/10.5281/zenodo.15332053)

# phidown

`phidown` is a Python package and CLI for searching and downloading Copernicus Data Space products and PhiSat-2 INSULA platform files.

It supports:
- Product search with OData filters (collection, dates, AOI, orbit direction, cloud cover).
- Product download through S3 (`s5cmd`).
- PhiSat-2 search and download through the INSULA platform.
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

### From source (uv)

```bash
git clone https://github.com/ESA-PhiLab/phidown.git
cd phidown
uv sync
```

Requirements:
- Python 3.9+
- `s5cmd` available on your `PATH` for S3 downloads

### As a Codex plugin

This repository now ships a repo-local Codex plugin and marketplace:

- `plugins/phidown/`
- `.agents/plugins/marketplace.json`

To install it from this repository:

1. Clone the repository and open the repo root in Codex.
2. Restart Codex if the plugin directory was already open before these files existed, so Codex reloads the repo marketplace.
3. Open the Codex plugin directory and select the `Phidown Plugins` marketplace.
4. Install the `Phidown Downloader` plugin.
5. Start a prompt such as:

```text
Use $phidown to search Copernicus products and download data via phidown CLI or Python.
```

If you manage marketplaces from the Codex CLI, you can also add this repository as a local marketplace root:

```bash
codex plugin marketplace add /absolute/path/to/phidown
```

### Local agent skills

Install the bundled phidown guidance for local agentic tools:

```bash
phidown skill add                 # Codex: $CODEX_HOME/skills/phidown
phidown skill add --engine claude # Claude Code: ~/.claude/skills/phidown
phidown skill add --engine cursor # Cursor project rule: .cursor/rules/phidown.mdc
phidown skill add --engine all
```

Remove the local files with the matching command:

```bash
phidown skill remove --engine all
```

## Credentials

Create a shared `.s5cfg` file for both CDSE and PhiSat-2. Keep the existing
`[default]` block for CDSE, then insert the `[phisat2]` block directly below
it in the same file:

```ini
[default]
aws_access_key_id = your_access_key
aws_secret_access_key = your_secret_key
aws_region = eu-central-1
host_base = eodata.dataspace.copernicus.eu
host_bucket = eodata.dataspace.copernicus.eu
use_https = true
check_ssl_certificate = true

[phisat2]
username = your_email@example.com
password = your_password
base_url = https://phisat2.insula.earth
api_base = https://phisat2.insula.earth/secure/api/v2.0
authorization_endpoint = https://identity.insula.earth/realms/phisat2/protocol/openid-connect/auth
token_endpoint = https://identity.insula.earth/realms/phisat2/protocol/openid-connect/token
redirect_uri = http://localhost:9207/auth
client_id = api-client
```

If credentials are not removed automatically, revoke them in the CDSE S3 Credentials Manager:
<https://eodata-s3keysmanager.dataspace.copernicus.eu/panel/s3-credentials>

`phidown --reset` updates only the active provider section, so CDSE and
PhiSat-2 credentials can coexist safely in one file.

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

### PhiSat-2 search

```python
from phidown.search import CopernicusDataSearcher

searcher = CopernicusDataSearcher()
searcher.query_by_filter(
    collection_name="PHISAT-2",
    product_type="L1",
    aoi_wkt="POLYGON((-3.90 40.30, -3.50 40.30, -3.50 40.70, -3.90 40.70, -3.90 40.30))",
    start_date="2026-05-01T00:00:00Z",
    end_date="2026-05-30T23:59:59Z",
    top=10,
    config_file=".s5cfg",
)

df = searcher.execute_query()
print(df[["Id", "coverage", "Name", "ContentDate", "DownloadUrl"]].head())
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

# Search PhiSat-2 products
phidown list --provider phisat2 --filter SESSION_ID_12345

# Download one PhiSat-2 product by exact filename or unique search token
phidown --provider phisat2 --name SESSION_ID_12345 -o ./data

# Burst coverage analysis
phidown --burst-coverage --bbox -5 40 5 45 --start-date 2024-08-02T00:00:00 --end-date 2024-08-15T23:59:59 --polarisation VV --format json
```

## Documentation

Full documentation: <https://esa-philab.github.io/phidown>

Useful entry points:
- Getting started: <https://esa-philab.github.io/phidown/getting_started.html>
- User guide: <https://esa-philab.github.io/phidown/user_guide.html>
- PhiSat-2 reference: <https://esa-philab.github.io/phidown/phisat2_reference.html>
- API reference: <https://esa-philab.github.io/phidown/api_reference.html>
- Burst mode guide: <https://esa-philab.github.io/phidown/sentinel1_burst_mode.html>

Notebook examples:
- `./how_to_start.ipynb`
- `./notebooks/`

## Contributing

Contributions are welcome. Please:
1. Fork the repository.
2. Create a feature branch.
3. Add tests and documentation updates where relevant.
4. Open a pull request with a clear description.

For bugs and questions, use:
- Issues: <https://github.com/ESA-PhiLab/phidown/issues>
- Discussions: <https://github.com/ESA-PhiLab/phidown/discussions>

## Citation

If you use `phidown` in research, please cite:

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
