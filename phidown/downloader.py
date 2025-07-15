from .s5cmd_utils import pull_down # old style, to be removed in future
import argparse
import sys
import logging
import os

# Configure logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)



def main() -> None:
    """Main function for command-line usage of s5cmd_utils.
    
    This function provides a simple CLI interface for downloading Sentinel-1 data
    from the Copernicus Data Space Ecosystem.
    """
    
    parser = argparse.ArgumentParser(
        description='Download Sentinel-1 data from Copernicus Data Space'
    )
    parser.add_argument(
        's3_path',
        help='S3 path to the Sentinel-1 data (should start with /eodata/)'
    )
    parser.add_argument(
        '-o', '--output-dir',
        default='.',
        help='Local output directory for downloaded files (default: current directory)'
    )
    parser.add_argument(
        '-c', '--config-file',
        default='.s5cfg',
        help='Path to s5cmd configuration file (default: .s5cfg)'
    )
    parser.add_argument(
        '-e', '--endpoint-url',
        default='https://eodata.dataspace.copernicus.eu',
        help='Copernicus Data Space endpoint URL'
    )
    parser.add_argument(
        '--no-download-all',
        action='store_true',
        help='Download only specific file instead of entire directory'
    )
    parser.add_argument(
        '--reset',
        action='store_true',
        help='Reset configuration file and prompt for new credentials'
    )
    
    args = parser.parse_args()
    
    try:
        success = pull_down(
            s3_path=args.s3_path,
            output_dir=os.path.abspath(args.output_dir),
            config_file=args.config_file,
            endpoint_url=args.endpoint_url,
            download_all=not args.no_download_all,
            reset=args.reset
        )
        
        if success:
            logger.info('Download completed successfully!')
            sys.exit(0)
        else:
            logger.error('Download failed!')
            sys.exit(1)
            
    except Exception as e:
        logger.error(f'Error during download: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()