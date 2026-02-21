from .s5cmd_utils import pull_down # old style, to be removed in future
import argparse
import sys
import logging
import os
from pathlib import Path
import requests
import uuid
import time


TOKEN_URL = 'https://identity.dataspace.copernicus.eu/auth/realms/cdse/protocol/openid-connect/token'
CLIENT_ID = 'cdse-public'

# Configure logger with rich formatting
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)
REQUEST_TIMEOUT_SECONDS = 30


class TokenManager:
    """Manages OAuth2 tokens with automatic refresh for Copernicus Data Space.
    
    This class handles token lifecycle including automatic refresh before expiration
    to ensure uninterrupted access to CDSE APIs during burst downloads.
    
    Attributes:
        username: CDSE account username.
        password: CDSE account password.
        token_url: OAuth2 token endpoint URL.
        client_id: OAuth2 client identifier.
        access_token: Current access token (None if not yet acquired).
        expiry: Token expiration time in epoch seconds.
        
    Example:
        >>> token_mgr = TokenManager('user@example.com', 'password')
        >>> token = token_mgr.get_access_token()
        >>> # Token is automatically refreshed when expired
        >>> token = token_mgr.get_access_token()
    """
    
    # Token expiry buffer in seconds to refresh before actual expiration
    EXPIRY_BUFFER_SECONDS = 60
    
    def __init__(self, username: str, password: str, 
                 token_url: str = TOKEN_URL, client_id: str = CLIENT_ID):
        """Initialize TokenManager with credentials.
        
        Args:
            username: CDSE account username.
            password: CDSE account password.
            token_url: OAuth2 token endpoint URL (default: CDSE token URL).
            client_id: OAuth2 client identifier (default: cdse-public).
        """
        self.username = username
        self.password = password
        self.token_url = token_url
        self.client_id = client_id
        self.access_token = None
        # Initialize expiry to current time to force initial token fetch
        self.expiry = time.time()

    def get_access_token(self) -> str:
        """Get current access token, refreshing if expired.
        
        This method checks if the current token is valid and refreshes it
        if necessary before returning.
        
        Returns:
            str: Valid access token for API requests.
            
        Raises:
            requests.exceptions.HTTPError: If token refresh fails.
        """
        if self.access_token is None or time.time() > self.expiry:
            self.refresh_access_token()
        return self.access_token

    def refresh_access_token(self) -> None:
        """Refresh the access token using password grant.
        
        This method authenticates with CDSE using username/password credentials
        to obtain a fresh access token. The expiry is set with a buffer
        to ensure tokens are refreshed before actual expiration.
        
        Raises:
            requests.exceptions.HTTPError: If authentication request fails.
        """
        logger.debug('Refreshing access token...')
        
        response = requests.post(
            self.token_url,
            data={
                'username': self.username,
                'password': self.password,
                'client_id': self.client_id,
                'grant_type': 'password'
            },
            timeout=REQUEST_TIMEOUT_SECONDS
        )
        response.raise_for_status()
        
        token_data = response.json()
        self.access_token = token_data['access_token']
        expires_in = token_data.get('expires_in', 3600)
        self.expiry = time.time() + expires_in - self.EXPIRY_BUFFER_SECONDS
        
        logger.debug('Access token refreshed successfully')


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
        ValueError: If username or password is empty.
        requests.exceptions.HTTPError: If the authentication request fails.
        
    Example:
        >>> token = get_token('myuser@example.com', 'mypassword')
        Acquired keycloak token!
    """
    if not username:
        raise ValueError('Username is required!')
    if not password:
        raise ValueError('Password is required!')

    logger.info('🔐 Authenticating with CDSE...')
    
    response = requests.post(
        TOKEN_URL,
        data={
            'client_id': CLIENT_ID,
            'username': username,
            'password': password,
            'grant_type': 'password',
        },
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()

    access_token = response.json()['access_token']
    logger.info('✅ Successfully acquired Keycloak token')

    return access_token



def download_burst_on_demand(
    burst_id: str,
    token,
    output_dir: Path,
    insecure_skip_verify: bool = False
) -> None:
    """Download and save a Sentinel-1 burst product from CDSE.
    
    This function requests on-demand processing of a single Sentinel-1 burst
    and downloads the resulting product as a ZIP file. The burst is identified
    by its UUID from the CDSE catalogue.
    
    Args:
        burst_id: UUID of the burst to download from the CDSE catalogue.
        token: Either a TokenManager instance or a string access token.
        output_dir: Directory path where the burst ZIP file will be saved.
        
    Raises:
        ValueError: If burst_id or token is empty.
        RuntimeError: If burst processing fails or returns non-200 status.
        
    Example:
        >>> from pathlib import Path
        >>> token_mgr = TokenManager('user@example.com', 'password')
        >>> download_burst('12345678-1234-1234-1234-123456789abc', token_mgr, Path('./output'))
        Processing burst...
        Processing has been successful!
        Saving output product...
        Output product has been saved to: ./output/burst_12345678.zip
    """
    if not burst_id:
        raise ValueError('Burst ID is required!')
    if not token:
        raise ValueError('Keycloak token is required!')

    try:
        uuid.UUID(burst_id)
    except ValueError:
        logger.error(f'❌ Invalid burst ID format: {burst_id}')
        raise ValueError('Burst ID is not a valid UUID!')

    logger.info(f'🛰️  Requesting on-demand processing for burst: {burst_id}')
    if insecure_skip_verify:
        logger.warning('⚠️  TLS certificate verification is disabled (insecure_skip_verify=True).')

    # Get token string from TokenManager or use token directly
    token_str = token.get_access_token() if isinstance(token, TokenManager) else token

    response = requests.post(
        f'https://catalogue.dataspace.copernicus.eu/odata/v1/Bursts({burst_id})/$value',
        headers={'Authorization': f'Bearer {token_str}'},
        verify=not insecure_skip_verify,
        allow_redirects=False,
        stream=True,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )

    if 300 <= response.status_code < 400:
        redirect_url = response.headers['Location']
        logger.debug(f'Following redirect to: {redirect_url}')
        # Refresh token for redirect request if using TokenManager
        token_str = token.get_access_token() if isinstance(token, TokenManager) else token
        response = requests.post(
            redirect_url,
            headers={'Authorization': f'Bearer {token_str}'},
            verify=not insecure_skip_verify,
            stream=True,
            allow_redirects=False,
            timeout=REQUEST_TIMEOUT_SECONDS,
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
