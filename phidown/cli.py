"""Command-line interface for phidown download operations.

This module provides a CLI for downloading Copernicus satellite data products
from the Copernicus Data Space Ecosystem using product names or S3 paths.
"""

import argparse
import sys
import os
import logging
import json
import time
import random
import warnings
from pathlib import Path
from typing import Optional, List, Sequence, Union

from .search import CopernicusDataSearcher
from .s5cmd_utils import pull_down
from .download_state import DownloadStateStore, default_state_file, is_product_complete
from .native_download import download_s3_resumable

# Configure logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def _compute_backoff_delay(attempt_index: int, backoff_base: float, backoff_max: float) -> float:
    """Compute retry delay with exponential backoff and jitter."""
    exponential = backoff_base * (2 ** attempt_index)
    return min(backoff_max, exponential) + random.uniform(0.0, 0.5)


def _dir_has_files(directory: str) -> bool:
    if not os.path.isdir(directory):
        return False
    return any(os.path.isfile(os.path.join(directory, name)) for name in os.listdir(directory))


def _warn_deprecated_option(option_name: str, replacement: str) -> None:
    warnings.warn(
        f'{option_name} is deprecated; use {replacement} instead.',
        DeprecationWarning,
        stacklevel=3,
    )


def _resolve_download_mode(
    mode: str = 'fast',
    *,
    resume_mode: Optional[str] = None,
    connect_timeout: float = 30.0,
    read_timeout: Optional[float] = None,
    robust: bool = False,
) -> str:
    if mode not in {'fast', 'safe'}:
        raise ValueError("mode must be either 'fast' or 'safe'")
    if resume_mode is not None and resume_mode not in {'off', 'product'}:
        raise ValueError("resume_mode must be either 'off' or 'product'")

    effective_mode = mode
    if robust:
        _warn_deprecated_option('--robust', '--mode safe')
        effective_mode = 'safe'
    if resume_mode is not None:
        _warn_deprecated_option('resume_mode/--resume-mode', 'mode/--mode')
        effective_mode = 'safe' if resume_mode == 'product' else 'fast'
    if effective_mode == 'fast' and (read_timeout is not None or float(connect_timeout) != 30.0):
        _warn_deprecated_option('connect_timeout/read_timeout', 'mode="safe"')
        effective_mode = 'safe'
    return effective_mode


def _parse_bbox_to_wkt(bbox: Union[str, Sequence[float]]) -> str:
    """Convert bbox values (csv string or 4-item sequence) to WKT polygon."""
    if isinstance(bbox, str):
        parts = [p.strip() for p in bbox.split(',')]
        if len(parts) != 4:
            raise ValueError('BBox must have exactly 4 comma-separated values: min_lon,min_lat,max_lon,max_lat')
        try:
            min_lon, min_lat, max_lon, max_lat = map(float, parts)
        except ValueError as exc:
            raise ValueError('BBox values must be numeric') from exc
    else:
        if len(bbox) != 4:
            raise ValueError('BBox must include 4 values: min_lon min_lat max_lon max_lat')
        min_lon, min_lat, max_lon, max_lat = map(float, bbox)

    if min_lon >= max_lon or min_lat >= max_lat:
        raise ValueError('BBox must satisfy min_lon < max_lon and min_lat < max_lat')

    return (
        f'POLYGON(('
        f'{min_lon} {min_lat}, '
        f'{max_lon} {min_lat}, '
        f'{max_lon} {max_lat}, '
        f'{min_lon} {max_lat}, '
        f'{min_lon} {min_lat}'
        f'))'
    )


def _parse_columns(columns: Optional[str]) -> Optional[List[str]]:
    """Parse comma-separated columns into a list."""
    if columns is None:
        return None
    parsed = [c.strip() for c in columns.split(',') if c.strip()]
    if not parsed:
        raise ValueError('If provided, --columns must contain at least one column name')
    return parsed


def download_by_name(
    product_name: str,
    output_dir: str,
    config_file: str = '.s5cfg',
    mode: str = 'fast',
    show_progress: bool = True,
    reset_config: bool = False,
    retry_count: int = 1,
    connect_timeout: float = 30.0,
    read_timeout: Optional[float] = None,
    state_file: Optional[str] = None,
    resume_mode: Optional[str] = None,
    s5cmd_retry_count: Optional[int] = None,
    max_workers: Optional[int] = None,
    backoff_base: float = 2.0,
    backoff_max: float = 60.0,
) -> bool:
    """Download a product by its name from Copernicus Data Space.
    
    Args:
        product_name: Full name of the Copernicus product to download.
        output_dir: Directory where the product will be downloaded.
        config_file: Path to s5cmd configuration file with credentials.
        mode: Download mode ('fast' for s5cmd, 'safe' for resumable native downloads).
        show_progress: Whether to display download progress bar.
        reset_config: Whether to reset configuration and prompt for credentials.
        retry_count: Number of command-level retry attempts.
        connect_timeout: Network connection timeout in seconds for native transfers.
        read_timeout: Network read timeout in seconds for native transfers.
        state_file: Optional JSON state file path for resumable runs.
        resume_mode: Deprecated legacy resume selector. Prefer ``mode``.
        s5cmd_retry_count: Optional internal retry count for s5cmd.
        max_workers: Optional worker count for s5cmd.
        backoff_base: Base delay in seconds for retry backoff.
        backoff_max: Max delay in seconds for retry backoff.
        
    Returns:
        bool: True if download was successful, False otherwise.
        
    Example:
        >>> success = download_by_name(
        ...     'S1A_IW_GRDH_1SDV_20240503T031926_20240503T031942_053701_0685FB_E003',
        ...     '/path/to/output'
        ... )
    """
    try:
        effective_mode = _resolve_download_mode(
            mode,
            resume_mode=resume_mode,
            connect_timeout=connect_timeout,
            read_timeout=read_timeout,
        )
        logger.info(f'🔍 Searching for product: {product_name}')
        
        # Search for the product
        searcher = CopernicusDataSearcher()
        df = searcher.query_by_name(product_name)
        
        if df.empty:
            logger.error(f'❌ Product not found: {product_name}')
            return False
        
        # Get product details
        s3_path = df.iloc[0]['S3Path']
        content_length = df.iloc[0].get('ContentLength', None)
        
        logger.info(f'✅ Found product in catalog')
        logger.info(f'📦 S3 Path: {s3_path}')
        
        if content_length:
            size_mb = content_length / (1024 * 1024)
            logger.info(f'📏 Size: {size_mb:.2f} MB')
        
        # Download the product
        logger.info(f'⬇️  Starting download to: {output_dir}')

        abs_output_dir = os.path.abspath(output_dir)
        safe_name = os.path.basename(s3_path.rstrip('/'))
        product_dir = os.path.join(abs_output_dir, safe_name)
        use_native = effective_mode == 'safe'

        state_store: Optional[DownloadStateStore] = None
        state_item_id = f'name:{product_name}'
        if not use_native and resume_mode not in (None, 'off'):
            resolved_state_file = state_file or default_state_file(abs_output_dir)
            state_store = DownloadStateStore(resolved_state_file)

            if is_product_complete(product_dir):
                state_store.mark(
                    state_item_id,
                    'success',
                    output_path=product_dir,
                    extra={'product_name': product_name, 's3_path': s3_path}
                )
                logger.info('⏭️  Product already downloaded, skipping.')
                return True

            existing = state_store.get(state_item_id)
            existing_output = existing.get('output_path') if isinstance(existing, dict) else None
            if existing and existing.get('status') == 'success' and existing_output and is_product_complete(existing_output):
                logger.info('⏭️  Product already downloaded (state file), skipping.')
                return True

        success = False
        attempts = max(1, int(retry_count))
        last_error = None
        should_reset_config = reset_config
        for attempt in range(attempts):
            try:
                if state_store is not None:
                    state_store.mark(
                        state_item_id,
                        'in_progress',
                        attempts=attempt + 1,
                        output_path=product_dir,
                        extra={'product_name': product_name, 's3_path': s3_path}
                    )

                if use_native:
                    attempt_reset = should_reset_config
                    should_reset_config = False
                    result = download_s3_resumable(
                        s3_path=s3_path,
                        output_dir=abs_output_dir,
                        config_file=config_file,
                        download_all=True,
                        state_file=state_file,
                        state_item_id=state_item_id,
                        connect_timeout=connect_timeout,
                        read_timeout=read_timeout,
                        show_progress=show_progress,
                        attempts=attempt + 1,
                        persist_state=True,
                        reset_config=attempt_reset,
                    )
                    if result.status == 'skipped':
                        logger.info('⏭️  Product already downloaded, skipping.')
                        return True
                    if not is_product_complete(result.output_path):
                        raise ValueError('manifest.safe not found - download may be incomplete')
                else:
                    attempt_reset = should_reset_config
                    should_reset_config = False
                    pull_down(
                        s3_path=s3_path,
                        output_dir=abs_output_dir,
                        config_file=config_file,
                        total_size=content_length,
                        show_progress=show_progress,
                        reset=attempt_reset,
                        retry_count=1,
                        s5cmd_retry_count=s5cmd_retry_count,
                        max_workers=max_workers,
                        backoff_base=backoff_base,
                        backoff_max=backoff_max,
                    )

                    if not is_product_complete(product_dir):
                        raise ValueError('manifest.safe not found - download may be incomplete')

                if state_store is not None:
                    state_store.mark(
                        state_item_id,
                        'success',
                        attempts=attempt + 1,
                        output_path=product_dir,
                        extra={'product_name': product_name, 's3_path': s3_path}
                    )
                success = True
                break
            except Exception as e:
                last_error = str(e)
                if state_store is not None:
                    state_store.mark(
                        state_item_id,
                        'failed',
                        attempts=attempt + 1,
                        output_path=product_dir,
                        error=last_error,
                        extra={'product_name': product_name, 's3_path': s3_path}
                    )
                if attempt < attempts - 1:
                    delay = _compute_backoff_delay(attempt, backoff_base=backoff_base, backoff_max=backoff_max)
                    logger.warning(
                        f'⚠️  Attempt {attempt + 1}/{attempts} failed ({e}). '
                        f'Retrying in {delay:.1f}s...'
                    )
                    time.sleep(delay)

        if success:
            logger.info('✅ Download completed successfully!')
        else:
            logger.error(f'❌ Download failed! {last_error}')
            
        return success
        
    except Exception as e:
        logger.error(f'❌ Error during download: {e}')
        return False


def download_by_s3path(
    s3_path: str,
    output_dir: str,
    config_file: str = '.s5cfg',
    mode: str = 'fast',
    show_progress: bool = True,
    reset_config: bool = False,
    download_all: bool = True,
    retry_count: int = 1,
    connect_timeout: float = 30.0,
    read_timeout: Optional[float] = None,
    state_file: Optional[str] = None,
    resume_mode: Optional[str] = None,
    s5cmd_retry_count: Optional[int] = None,
    max_workers: Optional[int] = None,
    backoff_base: float = 2.0,
    backoff_max: float = 60.0,
) -> bool:
    """Download a product directly using its S3 path.
    
    Args:
        s3_path: S3 path of the product (starting with /eodata/).
        output_dir: Directory where the product will be downloaded.
        config_file: Path to s5cmd configuration file with credentials.
        mode: Download mode ('fast' for s5cmd, 'safe' for resumable native downloads).
        show_progress: Whether to display download progress bar.
        reset_config: Whether to reset configuration and prompt for credentials.
        download_all: If True, downloads entire directory; otherwise specific file.
        retry_count: Number of command-level retry attempts.
        connect_timeout: Network connection timeout in seconds for native transfers.
        read_timeout: Network read timeout in seconds for native transfers.
        state_file: Optional JSON state file path for resumable runs.
        resume_mode: Deprecated legacy resume selector. Prefer ``mode``.
        s5cmd_retry_count: Optional internal retry count for s5cmd.
        max_workers: Optional worker count for s5cmd.
        backoff_base: Base delay in seconds for retry backoff.
        backoff_max: Max delay in seconds for retry backoff.
        
    Returns:
        bool: True if download was successful, False otherwise.
        
    Example:
        >>> success = download_by_s3path(
        ...     '/eodata/Sentinel-1/SAR/IW_GRDH_1S/2024/05/03/...',
        ...     '/path/to/output'
        ... )
    """
    try:
        if not s3_path.startswith('/eodata/'):
            logger.error(f'❌ Invalid S3 path format. Must start with /eodata/')
            return False
        effective_mode = _resolve_download_mode(
            mode,
            resume_mode=resume_mode,
            connect_timeout=connect_timeout,
            read_timeout=read_timeout,
        )
        
        logger.info(f'📦 S3 Path: {s3_path}')
        logger.info(f'⬇️  Starting download to: {output_dir}')

        abs_output_dir = os.path.abspath(output_dir)
        safe_name = os.path.basename(s3_path.rstrip('/'))
        target_dir = os.path.join(abs_output_dir, safe_name)
        use_native = effective_mode == 'safe'

        state_store: Optional[DownloadStateStore] = None
        state_item_id = f's3:{s3_path}'
        if not use_native and resume_mode not in (None, 'off'):
            resolved_state_file = state_file or default_state_file(abs_output_dir)
            state_store = DownloadStateStore(resolved_state_file)

            already_complete = is_product_complete(target_dir) if download_all else _dir_has_files(target_dir)
            if already_complete:
                state_store.mark(
                    state_item_id,
                    'success',
                    output_path=target_dir,
                    extra={'s3_path': s3_path}
                )
                logger.info('⏭️  Target already downloaded, skipping.')
                return True

            existing = state_store.get(state_item_id)
            existing_output = existing.get('output_path') if isinstance(existing, dict) else None
            if existing and existing.get('status') == 'success' and existing_output:
                complete_from_state = (
                    is_product_complete(existing_output) if download_all else _dir_has_files(existing_output)
                )
                if complete_from_state:
                    logger.info('⏭️  Target already downloaded (state file), skipping.')
                    return True

        success = False
        attempts = max(1, int(retry_count))
        last_error = None
        should_reset_config = reset_config
        for attempt in range(attempts):
            try:
                if state_store is not None:
                    state_store.mark(
                        state_item_id,
                        'in_progress',
                        attempts=attempt + 1,
                        output_path=target_dir,
                        extra={'s3_path': s3_path}
                    )

                if use_native:
                    attempt_reset = should_reset_config
                    should_reset_config = False
                    result = download_s3_resumable(
                        s3_path=s3_path,
                        output_dir=abs_output_dir,
                        config_file=config_file,
                        download_all=download_all,
                        state_file=state_file,
                        state_item_id=state_item_id,
                        connect_timeout=connect_timeout,
                        read_timeout=read_timeout,
                        show_progress=show_progress,
                        attempts=attempt + 1,
                        persist_state=True,
                        reset_config=attempt_reset,
                    )
                    if result.status == 'skipped':
                        logger.info('⏭️  Target already downloaded, skipping.')
                        return True
                    if download_all and not is_product_complete(result.output_path):
                        raise ValueError('manifest.safe not found - download may be incomplete')
                else:
                    attempt_reset = should_reset_config
                    should_reset_config = False
                    pull_down(
                        s3_path=s3_path,
                        output_dir=abs_output_dir,
                        config_file=config_file,
                        show_progress=show_progress,
                        reset=attempt_reset,
                        download_all=download_all,
                        retry_count=1,
                        s5cmd_retry_count=s5cmd_retry_count,
                        max_workers=max_workers,
                        backoff_base=backoff_base,
                        backoff_max=backoff_max,
                    )

                if state_store is not None:
                    state_store.mark(
                        state_item_id,
                        'success',
                        attempts=attempt + 1,
                        output_path=target_dir,
                        extra={'s3_path': s3_path}
                    )
                success = True
                break
            except Exception as e:
                last_error = str(e)
                if state_store is not None:
                    state_store.mark(
                        state_item_id,
                        'failed',
                        attempts=attempt + 1,
                        output_path=target_dir,
                        error=last_error,
                        extra={'s3_path': s3_path}
                    )
                if attempt < attempts - 1:
                    delay = _compute_backoff_delay(attempt, backoff_base=backoff_base, backoff_max=backoff_max)
                    logger.warning(
                        f'⚠️  Attempt {attempt + 1}/{attempts} failed ({e}). '
                        f'Retrying in {delay:.1f}s...'
                    )
                    time.sleep(delay)
        
        if success:
            logger.info('✅ Download completed successfully!')
        else:
            logger.error(f'❌ Download failed! {last_error}')
            
        return success
        
    except Exception as e:
        logger.error(f'❌ Error during download: {e}')
        return False


def list_products(
    collection: str,
    product_type: Optional[str] = None,
    orbit_direction: Optional[str] = None,
    cloud_cover: Optional[float] = None,
    aoi_wkt: Optional[str] = None,
    bbox: Optional[Union[str, Sequence[float]]] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    top: int = 50,
    order_by: str = "ContentDate/Start desc",
    output_format: str = "table",
    columns: Optional[str] = None,
    save_path: Optional[str] = None
) -> bool:
    """List products with AOI/date filters and optional output formats."""
    try:
        effective_aoi = aoi_wkt
        if bbox:
            effective_aoi = _parse_bbox_to_wkt(bbox)

        selected_columns = _parse_columns(columns)

        searcher = CopernicusDataSearcher()
        searcher.query_by_filter(
            collection_name=collection,
            product_type=product_type,
            orbit_direction=orbit_direction,
            cloud_cover_threshold=cloud_cover,
            aoi_wkt=effective_aoi,
            start_date=start_date,
            end_date=end_date,
            top=top,
            order_by=order_by
        )
        df = searcher.execute_query()

        if df.empty:
            logger.info('No products found for the selected filters.')
            return True

        if selected_columns:
            missing_columns = [col for col in selected_columns if col not in df.columns]
            if missing_columns:
                logger.error(f'Requested columns are not available: {", ".join(missing_columns)}')
                return False
            out_df = df[selected_columns]
        else:
            default_columns = [
                c for c in ['Name', 'S3Path', 'ContentDate', 'Collection', 'OriginDate', 'coverage'] if c in df.columns
            ]
            out_df = df[default_columns] if default_columns else df

        if output_format == 'json':
            rendered = out_df.to_json(orient='records', indent=2)
        elif output_format == 'csv':
            rendered = out_df.to_csv(index=False)
        else:
            rendered = out_df.to_string(index=False)

        if save_path:
            save_target = Path(save_path)
            save_target.parent.mkdir(parents=True, exist_ok=True)
            save_target.write_text(rendered, encoding='utf-8')
            logger.info(f'Saved {len(out_df)} products to: {save_target}')
        else:
            print(rendered)

        logger.info(f'Listed {len(out_df)} products.')
        return True

    except Exception as e:
        logger.error(f'❌ Error during listing: {e}')
        return False


def burst_coverage_analysis(
    aoi_wkt: Optional[str] = None,
    bbox: Optional[Union[str, Sequence[float]]] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    polarisation: str = 'VV',
    orbit_direction: Optional[str] = None,
    relative_orbit_number: Optional[int] = None,
    preferred_subswath: Optional[str] = None,
    output_format: str = 'table',
    columns: Optional[str] = None,
    save_path: Optional[str] = None
) -> bool:
    """Run Sentinel-1 burst coverage analysis over AOI and dates."""
    try:
        effective_aoi = aoi_wkt
        if bbox:
            effective_aoi = _parse_bbox_to_wkt(bbox)

        preferred = None
        if preferred_subswath:
            preferred = [item.strip().upper() for item in preferred_subswath.split(',') if item.strip()]
            if not preferred:
                raise ValueError('If provided, --preferred-subswath must contain at least one value')

        selected_columns = _parse_columns(columns)

        searcher = CopernicusDataSearcher()
        df = searcher.find_optimal_bursts(
            aoi_wkt=effective_aoi,
            start_date=start_date,
            end_date=end_date,
            polarisation=polarisation,
            orbit_direction=orbit_direction,
            relative_orbit_number=relative_orbit_number,
            preferred_subswath=preferred
        )

        if df.empty:
            logger.info('No bursts found for the selected filters.')
            return True

        if selected_columns:
            missing_columns = [col for col in selected_columns if col not in df.columns]
            if missing_columns:
                logger.error(f'Requested columns are not available: {", ".join(missing_columns)}')
                return False
            out_df = df[selected_columns]
        else:
            default_columns = [
                c for c in [
                    'Id', 'BurstId', 'SwathIdentifier', 'coverage', 'OrbitDirection',
                    'RelativeOrbitNumber', 'PolarisationChannels', 'ContentDate', 'S3Path'
                ] if c in df.columns
            ]
            out_df = df[default_columns] if default_columns else df

        swath_counts = {}
        if 'SwathIdentifier' in df.columns:
            swath_counts = {str(k): int(v) for k, v in df['SwathIdentifier'].value_counts().to_dict().items()}

        coverage_mean = None
        coverage_max = None
        if 'coverage' in df.columns:
            coverage_mean = float(df['coverage'].dropna().mean()) if not df['coverage'].dropna().empty else None
            coverage_max = float(df['coverage'].dropna().max()) if not df['coverage'].dropna().empty else None

        summary = {
            'total_bursts': int(len(df)),
            'orbit_direction': orbit_direction,
            'relative_orbit_number': relative_orbit_number,
            'polarisation': polarisation,
            'mean_coverage': coverage_mean,
            'max_coverage': coverage_max,
            'swath_counts': swath_counts,
        }

        if output_format == 'json':
            rendered = json.dumps(
                {'summary': summary, 'bursts': out_df.to_dict(orient='records')},
                indent=2,
                default=str
            )
        elif output_format == 'csv':
            rendered = out_df.to_csv(index=False)
        else:
            summary_lines = [
                f"total_bursts={summary['total_bursts']}",
                f"polarisation={summary['polarisation']}",
                f"mean_coverage={summary['mean_coverage']}",
                f"max_coverage={summary['max_coverage']}",
                f"swath_counts={summary['swath_counts']}",
                "",
            ]
            rendered = "\n".join(summary_lines) + out_df.to_string(index=False)

        if save_path:
            save_target = Path(save_path)
            save_target.parent.mkdir(parents=True, exist_ok=True)
            save_target.write_text(rendered, encoding='utf-8')
            logger.info(f'Saved burst analysis ({len(out_df)} rows) to: {save_target}')
        else:
            print(rendered)

        logger.info(f'Burst coverage analysis completed: {len(out_df)} rows.')
        return True

    except Exception as e:
        logger.error(f'❌ Error during burst coverage analysis: {e}')
        return False


def _validate_list_args(parser: argparse.ArgumentParser, args: argparse.Namespace, mode_label: str) -> None:
    """Validate required spatial/temporal args for list operations."""
    if args.aoi_wkt and args.bbox:
        parser.error('Use only one spatial filter: --aoi-wkt or --bbox')
    if not (args.aoi_wkt or args.bbox):
        parser.error(f'{mode_label} requires a spatial filter: --aoi-wkt or --bbox')
    if not (args.start_date or args.end_date):
        parser.error(f'{mode_label} requires at least one temporal filter: --start-date or --end-date')


def _main_list_subcommand(argv: Optional[Sequence[str]] = None) -> None:
    """Handle `phidown list ...` subcommand."""
    parser = argparse.ArgumentParser(
        prog='phidown list',
        description='List Copernicus products with AOI/date filters'
    )
    parser.add_argument('--collection', type=str, default='SENTINEL-1')
    parser.add_argument('--product-type', type=str)
    parser.add_argument('--orbit-direction', type=str, choices=['ASCENDING', 'DESCENDING'])
    parser.add_argument('--cloud-cover', type=float)
    parser.add_argument('--aoi-wkt', type=str)
    parser.add_argument(
        '--bbox',
        type=float,
        nargs=4,
        metavar=('MIN_LON', 'MIN_LAT', 'MAX_LON', 'MAX_LAT')
    )
    parser.add_argument('--start-date', type=str)
    parser.add_argument('--end-date', type=str)
    parser.add_argument('--top', type=int, default=50)
    parser.add_argument('--order-by', type=str, default='ContentDate/Start desc')
    parser.add_argument('--format', dest='output_format', choices=['table', 'json', 'csv'], default='table')
    parser.add_argument('--columns', type=str)
    parser.add_argument('--save', type=str)
    parser.add_argument('-v', '--verbose', action='store_true')

    args = parser.parse_args(argv)
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    _validate_list_args(parser, args, mode_label='list')

    success = list_products(
        collection=args.collection,
        product_type=args.product_type,
        orbit_direction=args.orbit_direction,
        cloud_cover=args.cloud_cover,
        aoi_wkt=args.aoi_wkt,
        bbox=args.bbox,
        start_date=args.start_date,
        end_date=args.end_date,
        top=args.top,
        order_by=args.order_by,
        output_format=args.output_format,
        columns=args.columns,
        save_path=args.save
    )
    sys.exit(0 if success else 1)


def main() -> None:
    """Main entry point for phidown CLI."""
    # Support subcommand-style UX: `phidown list ...`
    if len(sys.argv) > 1 and sys.argv[1] == 'list':
        try:
            _main_list_subcommand(sys.argv[2:])
        except KeyboardInterrupt:
            logger.warning('\n⚠️  Operation interrupted by user')
            sys.exit(130)
        except Exception as e:
            logger.error(f'❌ Fatal error: {e}')
            sys.exit(1)

    parser = argparse.ArgumentParser(
        prog='phidown',
        description='Download Copernicus satellite data from Data Space Ecosystem',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List products using subcommand style
  phidown list --collection SENTINEL-1 --product-type GRD --bbox -5 40 5 45 --start-date 2024-01-01T00:00:00 --end-date 2024-01-31T23:59:59

  # Download by product name
  phidown --name S1A_IW_GRDH_1SDV_20240503T031926_20240503T031942_053701_0685FB_E003 -o ./data
  
  # Download by S3 path
  phidown --s3path /eodata/Sentinel-1/SAR/IW_GRDH_1S/2024/05/03/... -o ./data

  # List products over AOI + date range
  phidown --list --collection SENTINEL-1 --product-type GRD --bbox -5 40 5 45 --start-date 2024-01-01T00:00:00 --end-date 2024-01-31T23:59:59

  # Burst coverage analysis over AOI + date range
  phidown --burst-coverage --bbox -5 40 5 45 --start-date 2024-08-02T00:00:00 --end-date 2024-08-15T23:59:59 --polarisation VV --format json
  
  # Reset configuration and enter new credentials
  phidown --name PRODUCT_NAME -o ./data --reset
  
  # Download without progress bar
  phidown --name PRODUCT_NAME -o ./data --no-progress
        """
    )
    
    # Input source (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        '--name',
        type=str,
        help='Product name to download (e.g., S1A_IW_GRDH_1SDV_...)'
    )
    input_group.add_argument(
        '--s3path',
        type=str,
        help='S3 path to download (must start with /eodata/)'
    )
    input_group.add_argument(
        '--list',
        action='store_true',
        help='List products using AOI/date filters'
    )
    input_group.add_argument(
        '--burst-coverage',
        action='store_true',
        help='Analyze Sentinel-1 burst coverage over AOI/date range'
    )
    
    # Output configuration
    parser.add_argument(
        '-o', '--output-dir',
        type=str,
        default='.',
        help='Output directory for downloaded data (default: current directory)'
    )
    
    # Configuration options
    parser.add_argument(
        '-c', '--config-file',
        type=str,
        default='.s5cfg',
        help='Path to s5cmd configuration file (default: .s5cfg)'
    )
    
    parser.add_argument(
        '--reset',
        action='store_true',
        help='Reset configuration file and prompt for new credentials'
    )
    parser.add_argument(
        '--mode',
        choices=['fast', 'safe'],
        default='fast',
        help='Download mode: fast uses s5cmd, safe uses resumable native downloads'
    )
    
    # Download options
    parser.add_argument(
        '--no-progress',
        action='store_true',
        help='Disable progress bar during download'
    )
    
    parser.add_argument(
        '--no-download-all',
        action='store_true',
        help='Download specific file instead of entire directory (for S3 path only)'
    )

    # Robustness options
    parser.add_argument(
        '--robust',
        action='store_true',
        help='Deprecated legacy preset. Prefer --mode safe'
    )
    parser.add_argument(
        '--retry-count',
        type=int,
        help='Number of command-level retry attempts for downloads'
    )
    parser.add_argument(
        '--connect-timeout',
        type=float,
        help='Network connection timeout in seconds'
    )
    parser.add_argument(
        '--read-timeout',
        type=float,
        help='Network read timeout in seconds'
    )
    parser.add_argument(
        '--resume-mode',
        choices=['off', 'product'],
        default=None,
        help='Deprecated legacy resume selector. Prefer --mode {fast,safe}'
    )
    parser.add_argument(
        '--state-file',
        type=str,
        help='Path to JSON state file used for resumable downloads'
    )
    parser.add_argument(
        '--s5cmd-retry-count',
        type=int,
        help='Internal retry count passed to s5cmd (--retry-count)'
    )
    parser.add_argument(
        '--max-workers',
        type=int,
        help='Number of workers passed to s5cmd (--numworkers)'
    )
    parser.add_argument(
        '--backoff-base',
        type=float,
        help='Base delay in seconds for exponential retry backoff'
    )
    parser.add_argument(
        '--backoff-max',
        type=float,
        help='Maximum delay in seconds for exponential retry backoff'
    )

    # Product listing options
    parser.add_argument(
        '--collection',
        type=str,
        default='SENTINEL-1',
        help='Collection to search when using --list (default: SENTINEL-1)'
    )
    parser.add_argument(
        '--product-type',
        type=str,
        help='Product type filter (e.g., GRD, SLC, S2MSI1C) for --list'
    )
    parser.add_argument(
        '--orbit-direction',
        type=str,
        choices=['ASCENDING', 'DESCENDING'],
        help='Orbit direction filter for --list/--burst-coverage'
    )
    parser.add_argument(
        '--cloud-cover',
        type=float,
        help='Cloud cover threshold (0-100) for --list'
    )
    parser.add_argument(
        '--aoi-wkt',
        type=str,
        help='AOI as WKT POLYGON for --list/--burst-coverage'
    )
    parser.add_argument(
        '--bbox',
        type=float,
        nargs=4,
        metavar=('MIN_LON', 'MIN_LAT', 'MAX_LON', 'MAX_LAT'),
        help='AOI bbox for --list/--burst-coverage as four values: MIN_LON MIN_LAT MAX_LON MAX_LAT'
    )
    parser.add_argument(
        '--start-date',
        type=str,
        help='Start date (ISO 8601) for --list/--burst-coverage'
    )
    parser.add_argument(
        '--end-date',
        type=str,
        help='End date (ISO 8601) for --list/--burst-coverage'
    )
    parser.add_argument(
        '--top',
        type=int,
        default=50,
        help='Maximum number of results for --list (default: 50)'
    )
    parser.add_argument(
        '--order-by',
        type=str,
        default='ContentDate/Start desc',
        help='Sort expression for --list (default: ContentDate/Start desc)'
    )
    parser.add_argument(
        '--format',
        dest='output_format',
        choices=['table', 'json', 'csv'],
        default='table',
        help='Output format for --list/--burst-coverage (default: table)'
    )
    parser.add_argument(
        '--columns',
        type=str,
        help='Comma-separated output columns for --list/--burst-coverage'
    )
    parser.add_argument(
        '--save',
        type=str,
        help='Save --list/--burst-coverage output to file instead of stdout'
    )
    parser.add_argument(
        '--polarisation',
        type=str,
        choices=['VV', 'VH', 'HH', 'HV'],
        default='VV',
        help='Polarisation filter for --burst-coverage (default: VV)'
    )
    parser.add_argument(
        '--relative-orbit-number',
        type=int,
        help='Relative orbit number filter for --burst-coverage'
    )
    parser.add_argument(
        '--preferred-subswath',
        type=str,
        help='Comma-separated subswath preference for --burst-coverage (e.g., IW1,IW2,IW3)'
    )
    
    # Verbosity
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s 0.1.25'
    )
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    effective_mode = _resolve_download_mode(
        args.mode,
        resume_mode=args.resume_mode,
        connect_timeout=args.connect_timeout if args.connect_timeout is not None else 30.0,
        read_timeout=args.read_timeout,
        robust=args.robust,
    )
    effective_retry_count = args.retry_count if args.retry_count is not None else (5 if effective_mode == 'safe' else 1)
    effective_connect_timeout = args.connect_timeout if args.connect_timeout is not None else 30.0
    effective_read_timeout = args.read_timeout if args.read_timeout is not None else (900.0 if effective_mode == 'safe' else None)
    effective_backoff_base = args.backoff_base if args.backoff_base is not None else 2.0
    effective_backoff_max = args.backoff_max if args.backoff_max is not None else 60.0
    effective_s5cmd_retry_count = (
        args.s5cmd_retry_count if args.s5cmd_retry_count is not None else (10 if effective_mode == 'safe' else None)
    )
    effective_max_workers = args.max_workers
    
    # Execute download based on input type
    try:
        if args.list:
            _validate_list_args(parser, args, mode_label='--list')

            success = list_products(
                collection=args.collection,
                product_type=args.product_type,
                orbit_direction=args.orbit_direction,
                cloud_cover=args.cloud_cover,
                aoi_wkt=args.aoi_wkt,
                bbox=args.bbox,
                start_date=args.start_date,
                end_date=args.end_date,
                top=args.top,
                order_by=args.order_by,
                output_format=args.output_format,
                columns=args.columns,
                save_path=args.save
            )
        elif args.burst_coverage:
            if args.aoi_wkt and args.bbox:
                parser.error('Use only one spatial filter: --aoi-wkt or --bbox')
            if not (args.aoi_wkt or args.bbox):
                parser.error('--burst-coverage requires a spatial filter: --aoi-wkt or --bbox')
            if not args.start_date or not args.end_date:
                parser.error('--burst-coverage requires both --start-date and --end-date')

            success = burst_coverage_analysis(
                aoi_wkt=args.aoi_wkt,
                bbox=args.bbox,
                start_date=args.start_date,
                end_date=args.end_date,
                polarisation=args.polarisation,
                orbit_direction=args.orbit_direction,
                relative_orbit_number=args.relative_orbit_number,
                preferred_subswath=args.preferred_subswath,
                output_format=args.output_format,
                columns=args.columns,
                save_path=args.save
            )
        elif args.name:
            # Create output directory only for download workflows
            output_path = Path(args.output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            success = download_by_name(
                product_name=args.name,
                output_dir=args.output_dir,
                config_file=args.config_file,
                mode=effective_mode,
                show_progress=not args.no_progress,
                reset_config=args.reset,
                retry_count=effective_retry_count,
                connect_timeout=effective_connect_timeout,
                read_timeout=effective_read_timeout,
                state_file=args.state_file,
                resume_mode=args.resume_mode,
                s5cmd_retry_count=effective_s5cmd_retry_count,
                max_workers=effective_max_workers,
                backoff_base=effective_backoff_base,
                backoff_max=effective_backoff_max,
            )
        elif args.s3path:
            # Create output directory only for download workflows
            output_path = Path(args.output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            success = download_by_s3path(
                s3_path=args.s3path,
                output_dir=args.output_dir,
                config_file=args.config_file,
                mode=effective_mode,
                show_progress=not args.no_progress,
                reset_config=args.reset,
                download_all=not args.no_download_all,
                retry_count=effective_retry_count,
                connect_timeout=effective_connect_timeout,
                read_timeout=effective_read_timeout,
                state_file=args.state_file,
                resume_mode=args.resume_mode,
                s5cmd_retry_count=effective_s5cmd_retry_count,
                max_workers=effective_max_workers,
                backoff_base=effective_backoff_base,
                backoff_max=effective_backoff_max,
            )
        else:
            parser.error('Provide one mode: --name, --s3path, --list, or --burst-coverage')
            sys.exit(1)
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        logger.warning('\n⚠️  Download interrupted by user')
        sys.exit(130)
    except Exception as e:
        logger.error(f'❌ Fatal error: {e}')
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
