---
name: phidown
description: Search, filter, and download Copernicus Data Space products with the phidown project. Use this skill when a user asks to find Sentinel products, query by AOI/date/product type, download by product name or S3 path, configure credentials (.s5cfg), troubleshoot phidown CLI/Python workflow issues, or prepare reproducible data-acquisition commands in the phidown repository.
---

# Phidown

## Overview
Use this skill to run reliable search and download workflows with the `phidown` repository.
Prefer deterministic commands, validate inputs early, and return reproducible download/search steps.

## Workflow

### 1. Confirm execution context
- Work from the phidown repo root.
- Check tooling before running downloads:
```bash
python --version
which s5cmd
python -m pip show phidown
```
- If `s5cmd` is missing, stop and report the blocker.

### 2. Choose operation mode
- Use CLI download by product name when the exact product name is known.
- Use CLI download by S3 path when catalog lookup is unnecessary.
- Use Python `CopernicusDataSearcher` when the user needs filtering by AOI/date/attributes.

### 3. Handle credentials safely
- Use `.s5cfg` for S3 downloads (CLI path).
- If missing, explain that phidown prompts for access key and secret key on first download or `--reset`.
- Never print secrets in output.

### 4. Execute with minimal, reproducible commands
- Download by name:
```bash
phidown --name "<PRODUCT_NAME>" -o "<OUTPUT_DIR>"
```
- Download by S3 path:
```bash
phidown --s3path "/eodata/..." -o "<OUTPUT_DIR>"
```
- Search first, then inspect top rows:
```python
from phidown.search import CopernicusDataSearcher

searcher = CopernicusDataSearcher()
searcher.query_by_filter(
    collection_name="SENTINEL-1",
    product_type="SLC",
    aoi_wkt="POLYGON((...))",
    start_date="2025-01-01T00:00:00",
    end_date="2025-01-31T23:59:59",
    top=100,
)
df = searcher.execute_query()
print(len(df))
print(df[["Name", "S3Path"]].head(5))
```

### 5. Verify outcome
- Confirm command exit status.
- Confirm expected files exist under output directory.
- Report what was downloaded (or why no product matched).

## Guardrails
- Keep paths absolute when scripting automation.
- Validate S3 path starts with `/eodata/` before invoking download.
- Validate AOI WKT is polygon and date strings are ISO 8601 when building search queries.
- Prefer targeted tests over full suite when network-heavy tests are present.

## Troubleshooting
- For empty search results, relax filters one at a time: AOI -> date range -> product type -> attributes.
- For auth failures, refresh `.s5cfg` using `--reset`.
- For download instability, retry with reduced scope (`--no-download-all` for S3 path mode).

## References
- For ready-to-run command patterns, read `references/commands.md`.
