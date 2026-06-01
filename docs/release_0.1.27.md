# Release 0.1.27

Date: 2026-04-20

## Summary
This release adds direct PhiSat-2 INSULA support to `phidown`, including search and download workflows in both the Python API and CLI, while preserving the existing CDSE behavior.

## New Features

### 1. PhiSat-2 provider integration
Added:

- `phidown.phisat2.PhiSat2Searcher`
- `phidown.PhiSat2Searcher` package export
- CLI provider selection with `--provider phisat2`

Supported workflows:

- Search by session ID, filename fragment, or other unique token
- Download by exact filename or unique match
- Shared credential handling through `.s5cfg`

### 2. Shared `.s5cfg` credentials
The credential file now supports both:

- `[default]` for CDSE S3 access
- `[phisat2]` for INSULA username/password access

The reset path now updates only the active provider section instead of overwriting unrelated credentials.

## Code Changes

Core package changes:

- Added `phidown/phisat2.py` for INSULA authentication, platform-file search, catalogue search, product resolution, HTTP download retries, optional unzip, and normalized PhiSat-2 result frames.
- Updated `phidown/search.py` so `CopernicusDataSearcher` recognizes `PHISAT-2` collection aliases, routes PhiSat-2 searches to `PhiSat2Searcher`, and supports PhiSat-2 downloads through the common `download_product()` path.
- Updated `phidown/cli.py` with `--provider {cdse,phisat2}`, PhiSat-2 list validation, PhiSat-2 download routing, and provider-specific reset behavior.
- Updated `phidown/s5cmd_utils.py` so `.s5cfg` updates preserve unrelated provider sections.
- Updated `phidown/__init__.py` to export `PhiSat2Searcher` lazily and report version `0.1.27`.
- Updated `pyproject.toml` to describe PhiSat-2 support, report version `0.1.27`, and include `InsulaWorkflowClient>=0.8.3`.

Behavior changes:

- `collection_name="PHISAT-2"` now uses the INSULA provider instead of the CDSE OData path.
- `phidown --provider phisat2 --name ...` resolves a unique PhiSat-2 token or exact filename before downloading.
- `phidown list --provider phisat2 --filter ...` lists INSULA platform-file matches.
- `phidown --provider phisat2 --s3path ...` is rejected because PhiSat-2 does not use CDSE S3 paths.

## File Change Inventory

New files:

- `phidown/phisat2.py`
- `tests/test_phisat2.py`
- `tests/conftest.py`
- `docs/release_0.1.27.md`

Updated source and packaging files:

- `phidown/__init__.py`
- `phidown/cli.py`
- `phidown/search.py`
- `phidown/s5cmd_utils.py`
- `pyproject.toml`

Updated tests:

- `tests/test_cli.py`
- `tests/test_cli_extended.py`
- `tests/test_package_init.py`
- `tests/test_s5cmd_utils.py`

Updated documentation:

- `readme.md`
- `docs/source/getting_started.rst`
- `docs/source/installation.rst`
- `docs/source/user_guide.rst`
- `docs/source/cli.rst`
- `docs/source/index.rst`
- `docs/source/api_reference.rst`
- `docs/source/changelog.rst`
- `docs/source/phisat2_reference.rst`

## Tests and Verification

### New tests
Added:

- `tests/test_phisat2.py`
- `tests/conftest.py`

Updated:

- `tests/test_cli.py`
- `tests/test_cli_extended.py`
- `tests/test_package_init.py`
- `tests/test_s5cmd_utils.py`

### Verification results

Targeted verification command:

- `pytest -q tests/test_phisat2.py tests/test_s5cmd_utils.py tests/test_cli.py tests/test_cli_extended.py tests/test_package_init.py`

Result:

- `83 passed`

## Documentation Updates

Updated user-facing docs:

- `readme.md`
- `docs/source/getting_started.rst`
- `docs/source/installation.rst`
- `docs/source/user_guide.rst`
- `docs/source/cli.rst`
- `docs/source/index.rst`
- `docs/source/api_reference.rst`
- `docs/source/changelog.rst`
- `docs/source/phisat2_reference.rst`
