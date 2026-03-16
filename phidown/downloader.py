from .s5cmd_utils import pull_down # old style, to be removed in future
import argparse
import sys
import logging
import os
from pathlib import Path
import requests
import uuid
import time
import random
from typing import Optional, Union

from .download_state import DownloadStateStore, default_state_file, is_non_empty_file


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


def _resolve_request_timeout(connect_timeout: Union[int, float], read_timeout: Optional[Union[int, float]]) -> Union[float, tuple]:
    """Build requests timeout value from connect/read values."""
    if read_timeout is None:
        return float(connect_timeout)
    return (float(connect_timeout), float(read_timeout))


def _compute_backoff_delay(attempt_index: int, backoff_base: float, backoff_max: float) -> float:
    """Compute retry delay with exponential backoff and jitter."""
    exponential = backoff_base * (2 ** attempt_index)
    return min(backoff_max, exponential) + random.uniform(0.0, 0.5)


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
    insecure_skip_verify: bool = False,
    connect_timeout: Union[int, float] = REQUEST_TIMEOUT_SECONDS,
    read_timeout: Optional[Union[int, float]] = None,
    retry_count: int = 1,
    backoff_base: float = 2.0,
    backoff_max: float = 60.0,
    state_file: Optional[str] = None,
    resume_mode: str = 'off',
) -> None:
    """Download and save a Sentinel-1 burst product from CDSE.
    
    This function requests on-demand processing of a single Sentinel-1 burst
    and downloads the resulting product as a ZIP file. The burst is identified
    by its UUID from the CDSE catalogue.
    
    Args:
        burst_id: UUID of the burst to download from the CDSE catalogue.
        token: Either a TokenManager instance or a string access token.
        output_dir: Directory path where the burst ZIP file will be saved.
        connect_timeout: HTTP connection timeout (seconds).
        read_timeout: HTTP read timeout (seconds). If None, uses connect_timeout.
        retry_count: Number of retry attempts on transient failures.
        backoff_base: Base delay in seconds for exponential backoff.
        backoff_max: Max delay in seconds for exponential backoff.
        state_file: Optional path to JSON state file for resumable runs.
        resume_mode: Resume mode ('off' or 'product').
        
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
    if resume_mode not in {'off', 'product'}:
        raise ValueError("resume_mode must be either 'off' or 'product'")

    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        uuid.UUID(burst_id)
    except ValueError:
        logger.error(f'❌ Invalid burst ID format: {burst_id}')
        raise ValueError('Burst ID is not a valid UUID!')

    logger.info(f'🛰️  Requesting on-demand processing for burst: {burst_id}')
    if insecure_skip_verify:
        logger.warning('⚠️  TLS certificate verification is disabled (insecure_skip_verify=True).')

    timeout_value = _resolve_request_timeout(connect_timeout=connect_timeout, read_timeout=read_timeout)
    attempts = max(1, int(retry_count))
    state_store: Optional[DownloadStateStore] = None
    if resume_mode != 'off':
        resolved_state_file = state_file or default_state_file(str(output_dir))
        state_store = DownloadStateStore(resolved_state_file)
        existing = state_store.get(burst_id)
        existing_output = existing.get('output_path') if isinstance(existing, dict) else None
        if existing and existing.get('status') == 'success' and existing_output and is_non_empty_file(existing_output):
            logger.info(f'⏭️  Burst {burst_id} already downloaded, skipping.')
            return

    def _post_with_token(url: str, force_refresh: bool = False, range_start: Optional[int] = None):
        if isinstance(token, TokenManager):
            if force_refresh:
                token.refresh_access_token()
            token_str = token.get_access_token()
        else:
            token_str = token
        headers = {'Authorization': f'Bearer {token_str}'}
        if range_start is not None and range_start > 0:
            headers['Range'] = f'bytes={range_start}-'

        return requests.post(
            url,
            headers=headers,
            verify=not insecure_skip_verify,
            allow_redirects=False,
            stream=True,
            timeout=timeout_value,
        )

    def _post_with_auth_retry(url: str, range_start: Optional[int] = None):
        response = _post_with_token(url, range_start=range_start)
        if response.status_code in (401, 403) and isinstance(token, TokenManager):
            logger.warning(
                f'⚠️  Received {response.status_code} from burst API. Refreshing token and retrying once.'
            )
            response = _post_with_token(url, force_refresh=True, range_start=range_start)
        return response

    last_error: Optional[Exception] = None
    for attempt in range(attempts):
        output_path: Optional[Path] = None
        temp_output_path: Optional[Path] = None
        try:
            if state_store is not None:
                state_store.mark(
                    burst_id,
                    'in_progress',
                    attempts=attempt + 1,
                    extra={'burst_id': burst_id},
                )

            existing_record = state_store.get(burst_id) if state_store is not None else None
            existing_output = existing_record.get('output_path') if isinstance(existing_record, dict) else None
            existing_temp_output = (
                Path(existing_output).with_suffix(Path(existing_output).suffix + '.part')
                if existing_output else None
            )
            resume_from = 0
            if existing_temp_output is not None and existing_temp_output.exists():
                resume_from = existing_temp_output.stat().st_size

            response = _post_with_auth_retry(
                f'https://catalogue.dataspace.copernicus.eu/odata/v1/Bursts({burst_id})/$value'
                ,
                range_start=resume_from,
            )

            if 300 <= response.status_code < 400:
                redirect_url = response.headers['Location']
                logger.debug(f'Following redirect to: {redirect_url}')
                response = _post_with_auth_retry(redirect_url, range_start=resume_from)

            if resume_from > 0 and response.status_code != 206:
                logger.warning('⚠️  Burst endpoint did not honor range request. Restarting from byte 0.')
                resume_from = 0
                if existing_temp_output is not None and existing_temp_output.exists():
                    existing_temp_output.unlink()
                response = _post_with_auth_retry(
                    f'https://catalogue.dataspace.copernicus.eu/odata/v1/Bursts({burst_id})/$value'
                )
                if 300 <= response.status_code < 400:
                    redirect_url = response.headers['Location']
                    response = _post_with_auth_retry(redirect_url)

            if response.status_code not in (200, 206):
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
            temp_output_path = output_path.with_suffix(output_path.suffix + '.part')
            logger.info(f'💾 Downloading burst to: {output_path}')

            total_size = resume_from
            write_mode = 'ab' if resume_from > 0 else 'wb'
            with open(temp_output_path, write_mode) as target_file:
                for chunk in response.iter_content(chunk_size=8192):
                    if not chunk:
                        continue
                    target_file.write(chunk)
                    total_size += len(chunk)

            if total_size <= 0:
                raise RuntimeError('Burst download produced an empty file')

            os.replace(temp_output_path, output_path)
            size_mb = total_size / (1024 * 1024)
            logger.info(f'✅ Successfully saved burst product ({size_mb:.2f} MB)')

            if state_store is not None:
                state_store.mark(
                    burst_id,
                    'success',
                    attempts=attempt + 1,
                    output_path=str(output_path),
                    extra={'size_bytes': total_size, 'partial_bytes': total_size},
                )
            return
        except Exception as exc:
            last_error = exc
            if state_store is not None:
                partial_bytes = None
                if temp_output_path is not None and temp_output_path.exists():
                    partial_bytes = temp_output_path.stat().st_size
                state_store.mark(
                    burst_id,
                    'failed',
                    attempts=attempt + 1,
                    error=str(exc),
                    output_path=str(output_path) if output_path is not None else None,
                    extra={'partial_bytes': partial_bytes} if partial_bytes is not None else None,
                )

            should_retry = attempt < attempts - 1 and not isinstance(exc, ValueError)
            if should_retry:
                delay = _compute_backoff_delay(attempt, backoff_base=backoff_base, backoff_max=backoff_max)
                logger.warning(
                    f'⚠️  Burst download attempt {attempt + 1}/{attempts} failed ({exc}). '
                    f'Retrying in {delay:.1f}s...'
                )
                time.sleep(delay)
            else:
                raise

    if last_error is not None:
        raise last_error


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
