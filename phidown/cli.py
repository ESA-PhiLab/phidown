"""Command-line interface for phidown download operations.

This module provides a CLI for downloading Copernicus satellite data products
from the Copernicus Data Space Ecosystem using product names or S3 paths.
"""

import argparse
import sys
import os
import logging
from pathlib import Path
from typing import Optional

from .search import CopernicusDataSearcher
from .s5cmd_utils import pull_down

# Configure logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def download_by_name(
    product_name: str,
    output_dir: str,
    config_file: str = '.s5cfg',
    show_progress: bool = True,
    reset_config: bool = False
) -> bool:
    """Download a product by its name from Copernicus Data Space.
    
    Args:
        product_name: Full name of the Copernicus product to download.
        output_dir: Directory where the product will be downloaded.
        config_file: Path to s5cmd configuration file with credentials.
        show_progress: Whether to display download progress bar.
        reset_config: Whether to reset configuration and prompt for credentials.
        
    Returns:
        bool: True if download was successful, False otherwise.
        
    Example:
        >>> success = download_by_name(
        ...     'S1A_IW_GRDH_1SDV_20240503T031926_20240503T031942_053701_0685FB_E003',
        ...     '/path/to/output'
        ... )
    """
    try:
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
        
        success = pull_down(
            s3_path=s3_path,
            output_dir=os.path.abspath(output_dir),
            config_file=config_file,
            total_size=content_length,
            show_progress=show_progress,
            reset=reset_config
        )
        
        if success:
            logger.info('✅ Download completed successfully!')
        else:
            logger.error('❌ Download failed!')
            
        return success
        
    except Exception as e:
        logger.error(f'❌ Error during download: {e}')
        return False


def download_by_s3path(
    s3_path: str,
    output_dir: str,
    config_file: str = '.s5cfg',
    show_progress: bool = True,
    reset_config: bool = False,
    download_all: bool = True
) -> bool:
    """Download a product directly using its S3 path.
    
    Args:
        s3_path: S3 path of the product (starting with /eodata/).
        output_dir: Directory where the product will be downloaded.
        config_file: Path to s5cmd configuration file with credentials.
        show_progress: Whether to display download progress bar.
        reset_config: Whether to reset configuration and prompt for credentials.
        download_all: If True, downloads entire directory; otherwise specific file.
        
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
        
        logger.info(f'📦 S3 Path: {s3_path}')
        logger.info(f'⬇️  Starting download to: {output_dir}')
        
        success = pull_down(
            s3_path=s3_path,
            output_dir=os.path.abspath(output_dir),
            config_file=config_file,
            show_progress=show_progress,
            reset=reset_config,
            download_all=download_all
        )
        
        if success:
            logger.info('✅ Download completed successfully!')
        else:
            logger.error('❌ Download failed!')
            
        return success
        
    except Exception as e:
        logger.error(f'❌ Error during download: {e}')
        return False


def main() -> None:
    """Main entry point for phidown CLI."""
    parser = argparse.ArgumentParser(
        prog='phidown',
        description='Download Copernicus satellite data from Data Space Ecosystem',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download by product name
  phidown --name S1A_IW_GRDH_1SDV_20240503T031926_20240503T031942_053701_0685FB_E003 -o ./data
  
  # Download by S3 path
  phidown --s3path /eodata/Sentinel-1/SAR/IW_GRDH_1S/2024/05/03/... -o ./data
  
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
    
    # Verbosity
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s 0.1.19'
    )
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create output directory if it doesn't exist
    output_path = Path(args.output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Execute download based on input type
    try:
        if args.name:
            success = download_by_name(
                product_name=args.name,
                output_dir=args.output_dir,
                config_file=args.config_file,
                show_progress=not args.no_progress,
                reset_config=args.reset
            )
        elif args.s3path:
            success = download_by_s3path(
                s3_path=args.s3path,
                output_dir=args.output_dir,
                config_file=args.config_file,
                show_progress=not args.no_progress,
                reset_config=args.reset,
                download_all=not args.no_download_all
            )
        else:
            parser.error('Either --name or --s3path must be provided')
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
