#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd -P)"

if [[ -n "${CONDA_BASE:-}" && -n "${ENV_PREFIX:-}" && -f "${CONDA_BASE}/bin/activate" ]]; then
  # The Makefile activates the env before calling this script; this keeps direct
  # script invocation and PBS execution deterministic too.
  source "${CONDA_BASE}/bin/activate"
  conda activate "${ENV_PREFIX}"
fi

BASE_DIR="${BASE_DIR:-${PROJECT_ROOT}}"
DATA_DIR="${DATA_DIR:-${BASE_DIR}/input_data}"
PY_SCRIPT_DIR="${PY_SCRIPT_DIR:-${BASE_DIR}/sarpyx/pyscripts}"
OUTPUT_PATH="${OUTPUT_PATH:-${OUTPUT_DIR:-${BASE_DIR}/OUT/worldsar_output}}"
OUTPUT_DIR="${OUTPUT_DIR:-${OUTPUT_PATH}}"
CUTS_OUTDIR="${CUTS_OUTDIR:-${TILES_DIR:-${BASE_DIR}/OUT/tiles}}"
TILES_DIR="${TILES_DIR:-${CUTS_OUTDIR}}"
DB_DIR="${DB_DIR:-${BASE_DIR}/OUT/DB}"
ENV_DIR="${ENV_DIR:-${BASE_DIR}/envs/worldsar-py313}"
SNAP_USER_DIR="${SNAP_USER_DIR:-${ENV_DIR}/opt/.snap}"
GRID_PATH="${GRID_PATH:-${BASE_DIR}/grid/grid_10km.geojson}"
GPT_MEMORY="${GPT_MEMORY:-64G}"
GPT_PARALLELISM="${GPT_PARALLELISM:-16}"
GPT_TIMEOUT="${GPT_TIMEOUT:-3600}"
SENTINEL_SUBAPS="${SENTINEL_SUBAPS:-2}"

PRODUCT_INPUT="${1:-${PRODUCT:-${WORLDSAR_PRODUCT:-}}}"
if [[ -z "${PRODUCT_INPUT}" ]]; then
  echo "ERROR: Product name is required." >&2
  echo "Usage: ${0##*/} <product_name>" >&2
  echo "Or set PRODUCT=<product_name_or_path>" >&2
  exit 2
fi

if [[ "${PRODUCT_INPUT}" == */* ]]; then
  PROD_PATH="${PRODUCT_INPUT}"
  PRODUCT_FROM_DATA_DIR=0
else
  PROD_PATH="${DATA_DIR}/${PRODUCT_INPUT}"
  PRODUCT_FROM_DATA_DIR=1
fi

if [[ -z "${GPT_PATH:-}" ]]; then
  GPT_PATH="$(command -v gpt || true)"
fi

[[ -d "${BASE_DIR}" ]] || { echo "ERROR: BASE_DIR not found: ${BASE_DIR}" >&2; exit 2; }
if [[ "${PRODUCT_FROM_DATA_DIR}" -eq 1 ]]; then
  [[ -d "${DATA_DIR}" ]] || { echo "ERROR: DATA_DIR not found: ${DATA_DIR}" >&2; exit 2; }
fi
[[ -d "${PY_SCRIPT_DIR}" ]] || { echo "ERROR: PY_SCRIPT_DIR not found: ${PY_SCRIPT_DIR}" >&2; exit 2; }
[[ -e "${PROD_PATH}" ]] || { echo "ERROR: Product not found: ${PROD_PATH}" >&2; exit 2; }
[[ -d "${SNAP_USER_DIR}" ]] || { echo "ERROR: SNAP_USER_DIR not found: ${SNAP_USER_DIR}" >&2; exit 2; }
[[ -f "${GRID_PATH}" ]] || { echo "ERROR: GRID_PATH not found: ${GRID_PATH}" >&2; exit 2; }
[[ -n "${GPT_PATH}" ]] || { echo "ERROR: gpt not found in PATH and GPT_PATH is unset." >&2; exit 2; }
if [[ "${GPT_PATH}" == */* ]]; then
  [[ -x "${GPT_PATH}" ]] || { echo "ERROR: GPT_PATH is not executable: ${GPT_PATH}" >&2; exit 2; }
else
  command -v "${GPT_PATH}" >/dev/null 2>&1 || { echo "ERROR: GPT command not found: ${GPT_PATH}" >&2; exit 2; }
fi

if command -v sarpyx >/dev/null 2>&1; then
  SARPYX_CMD=(sarpyx)
else
  SARPYX_CMD=(python -m sarpyx.cli.worldsar)
fi

read -r -a SENTINEL_SUBAP_ARGS <<< "${SENTINEL_SUBAPS}"
for subap in "${SENTINEL_SUBAP_ARGS[@]}"; do
  [[ "${subap}" =~ ^[0-9]+$ ]] || { echo "ERROR: SENTINEL_SUBAPS must contain integers: ${SENTINEL_SUBAPS}" >&2; exit 2; }
  [[ "${subap}" -ge 2 ]] || { echo "ERROR: SENTINEL_SUBAPS values must be >= 2: ${SENTINEL_SUBAPS}" >&2; exit 2; }
done

mkdir -p "${OUTPUT_PATH}" "${CUTS_OUTDIR}" "${DB_DIR}"
export SNAP_USERDIR="${SNAP_USER_DIR}"

args=(
  --input "${PROD_PATH}"
  --output "${OUTPUT_PATH}"
  --cuts-outdir "${CUTS_OUTDIR}"
  --gpt-path "${GPT_PATH}"
  --grid-path "${GRID_PATH}"
  --db-dir "${DB_DIR}"
  --gpt-memory "${GPT_MEMORY}"
  --gpt-parallelism "${GPT_PARALLELISM}"
  --gpt-timeout "${GPT_TIMEOUT}"
  --snap-userdir "${SNAP_USER_DIR}"
  --sentinel-subaps "${SENTINEL_SUBAP_ARGS[@]}"
)

[[ -n "${ORBIT_TYPE:-}" ]] && args+=(--orbit-type "${ORBIT_TYPE}")
[[ "${ORBIT_CONTINUE_ON_FAIL:-0}" == "1" ]] && args+=(--orbit-continue-on-fail)
[[ -n "${SENTINEL_SWATH:-}" ]] && args+=(--sentinel-swath "${SENTINEL_SWATH}")
[[ -n "${SENTINEL_FIRST_BURST:-}" ]] && args+=(--sentinel-first-burst "${SENTINEL_FIRST_BURST}")
[[ -n "${SENTINEL_LAST_BURST:-}" ]] && args+=(--sentinel-last-burst "${SENTINEL_LAST_BURST}")
[[ -n "${SENTINEL_TC_SOURCE_BAND:-}" ]] && args+=(--sentinel-tc-source-band "${SENTINEL_TC_SOURCE_BAND}")
[[ "${SKIP_PREPROCESSING:-0}" == "1" ]] && args+=(--skip-preprocessing)

echo "WORLDSAR_MODE=${WORLDSAR_MODE:-}"
echo "BASE_DIR=${BASE_DIR}"
echo "DATA_DIR=${DATA_DIR}"
echo "PROD_PATH=${PROD_PATH}"
echo "OUTPUT_PATH=${OUTPUT_PATH}"
echo "CUTS_OUTDIR=${CUTS_OUTDIR}"
echo "DB_DIR=${DB_DIR}"
echo "SNAP_USER_DIR=${SNAP_USER_DIR}"
echo "GRID_PATH=${GRID_PATH}"
echo "GPT_PATH=${GPT_PATH}"
echo "SARPYX_CMD=${SARPYX_CMD[*]}"

exec "${SARPYX_CMD[@]}" "${args[@]}"
