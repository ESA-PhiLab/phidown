# Release 0.1.25

Date: 2026-02-21

## Summary
This release expands the CLI from download-only operations to full discovery and burst analysis workflows, and adds extensive automated verification around CLI behavior.

## New CLI Features

### 1. Product listing over area and dates
Added a new CLI mode:

- `--list`

Supported filters and output controls:

- Spatial filters: `--aoi-wkt` or `--bbox MIN_LON MIN_LAT MAX_LON MAX_LAT`
- Temporal filters: `--start-date`, `--end-date`
- Product filters: `--collection`, `--product-type`, `--orbit-direction`, `--cloud-cover`
- Query controls: `--top`, `--order-by`
- Output controls: `--format {table,json,csv}`, `--columns`, `--save`

### 2. Burst coverage analysis over area and dates
Added a new CLI mode:

- `--burst-coverage`

Supported controls:

- Spatial filters: `--aoi-wkt` or `--bbox`
- Temporal filters: `--start-date` and `--end-date` (both required)
- Burst filters: `--polarisation`, `--orbit-direction`, `--relative-orbit-number`, `--preferred-subswath`
- Output controls: `--format {table,json,csv}`, `--columns`, `--save`

The mode computes burst-level output plus summary information (total bursts, swath counts, mean/max coverage when available).

## Tests and Verification

### New tests
Added:

- `tests/test_cli_extended.py`

Coverage includes:

- helper parser validation (`_parse_bbox_to_wkt`, `_parse_columns`)
- list mode edge cases (empty results, missing columns, save output, error handling)
- burst coverage edge cases (summary output, JSON save, preferred subswath parsing, error handling)
- main CLI validation (conflicting spatial args, missing required args, interrupt handling)

Updated:

- `tests/test_cli.py`

## Verification results
Repeated CLI-focused verification:

- Command:
  - `pytest -q tests/test_cli.py tests/test_cli_extended.py`
- Result (3 consecutive runs):
  - `42 passed`

Artifacts:

- `outputs/final/20260221_163659/cli_suite_run_1.txt`
- `outputs/final/20260221_163659/cli_suite_run_2.txt`
- `outputs/final/20260221_163659/cli_suite_run_3.txt`

## Documentation Updates

Updated user-facing docs to reflect the new CLI capabilities:

- `docs/source/cli.rst`
- `docs/source/user_guide.rst`
- `README.md`

## Skill Updates

Updated phidown skill guidance and command patterns to include list and burst-coverage workflows:

- `skills/phidown/SKILL.md`
- `skills/phidown/references/commands.md`

The same skill updates were synced to the active local skill path under `$CODEX_HOME/skills/phidown`.

