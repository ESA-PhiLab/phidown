from .s5cmd_utils import pull_down # old style, to be removed in future
import argparse
import sys
import logging
import os
from pathlib import Path
import requests
import urllib3
import uuid

urllib3.disable_warnings()


TOKEN_URL = 'https://identity.dataspace.copernicus.eu/auth/realms/cdse/protocol/openid-connect/token'
CLIENT_ID = 'cdse-public'

# Configure logger with rich formatting
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


# Implementation based on https://github.com/eu-cdse/notebook-samples/blob/main/geo/bursts_processing_on_demand.ipynb
def get_token(username: str, password: str) -> str:
    """Acquire an access token from Copernicus Data Space Ecosystem.
    
    This function authenticates with the CDSE identity service using username
    and password credentials to obtain a Keycloak access token for API access.
    
    Args:
        username: CDSE account username.
        password: CDSE account password.
        
    Returns:
        str: The access token string to be used for authenticated API requests.
        
    Raises:
        AssertionError: If username or password is empty.
        requests.exceptions.HTTPError: If the authentication request fails.
        
    Example:
        >>> token = get_token('myuser@example.com', 'mypassword')
        Acquired keycloak token!
    """
    assert username, 'Username is required!'
    assert password, 'Password is required!'

    logger.info('🔐 Authenticating with CDSE...')
    
    response = requests.post(
        TOKEN_URL,
        data={
            'client_id': CLIENT_ID,
            'username': username,
            'password': password,
            'grant_type': 'password',
        },
    )
    response.raise_for_status()

    access_token = response.json()['access_token']
    logger.info('✅ Successfully acquired Keycloak token')

    return access_token



def download_burst_on_demand(burst_id: str, token: str, output_dir: Path) -> None:
    """Download and save a Sentinel-1 burst product from CDSE.
    
    This function requests on-demand processing of a single Sentinel-1 burst
    and downloads the resulting product as a ZIP file. The burst is identified
    by its UUID from the CDSE catalogue.
    
    Args:
        burst_id: UUID of the burst to download from the CDSE catalogue.
        token: Keycloak access token obtained from get_token().
        output_dir: Directory path where the burst ZIP file will be saved.
        
    Raises:
        AssertionError: If burst_id or token is empty.
        RuntimeError: If burst processing fails or returns non-200 status.
        
    Example:
        >>> from pathlib import Path
        >>> token = get_token('user@example.com', 'password')
        >>> download_burst('12345678-1234-1234-1234-123456789abc', token, Path('./output'))
        Processing burst...
        Processing has been successful!
        Saving output product...
        Output product has been saved to: ./output/burst_12345678.zip
    """
    assert burst_id, 'Burst ID is required!'
    assert token, 'Keycloak token is required!'

    try:
        uuid.UUID(burst_id)
    except ValueError:
        logger.error(f'❌ Invalid burst ID format: {burst_id}')
        raise ValueError('Burst ID is not a valid UUID!')

    logger.info(f'🛰️  Requesting on-demand processing for burst: {burst_id}')

    response = requests.post(
        f'https://catalogue.dataspace.copernicus.eu/odata/v1/Bursts({burst_id})/$value',
        headers={'Authorization': f'Bearer {token}'},
        verify=False,
        allow_redirects=False,
        stream=True,
    )

    if 300 <= response.status_code < 400:
        redirect_url = response.headers['Location']
        logger.debug(f'Following redirect to: {redirect_url}')
        response = requests.post(
            redirect_url,
            headers={'Authorization': f'Bearer {token}'},
            verify=False,
            stream=True,
            allow_redirects=False,
        )

    if response.status_code != 200:
        err_msg = (
            response.json()
            if response.headers.get('Content-Type') == 'application/json'
            else response.text
        )
        logger.error(f'❌ Burst processing failed with status {response.status_code}')
        raise RuntimeError(f'Failed to process burst: \n{err_msg}')

    logger.info('✅ Burst processing completed successfully')

    try:
        zipfile_name = response.headers['Content-Disposition'].split('filename=')[1]
    except (KeyError, IndexError):
        zipfile_name = 'output_burst.zip'
        logger.warning(f'⚠️  Could not extract filename from headers, using default: {zipfile_name}')

    output_path = output_dir / zipfile_name
    logger.info(f'💾 Downloading burst to: {output_path}')
    
    total_size = 0
    with open(output_path, 'wb') as target_file:
        for chunk in response.iter_content(chunk_size=8192):
            target_file.write(chunk)
            total_size += len(chunk)
    
    size_mb = total_size / (1024 * 1024)
    logger.info(f'✅ Successfully saved burst product ({size_mb:.2f} MB)')


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
            logger.info('✅ Download completed successfully!')
            sys.exit(0)
        else:
            logger.error('❌ Download failed!')
            sys.exit(1)
            
    except Exception as e:
        logger.error(f'❌ Error during download: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()