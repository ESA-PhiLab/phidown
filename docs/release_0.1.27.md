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

- `78 passed`

## Documentation Updates

Updated user-facing docs:

- `readme.md`
- `docs/source/getting_started.rst`
- `docs/source/installation.rst`
- `docs/source/user_guide.rst`
- `docs/source/cli.rst`
- `docs/source/index.rst`
- `docs/source/changelog.rst`
