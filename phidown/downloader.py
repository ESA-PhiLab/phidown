#!/usr/bin/env python3
# S3 Credentials: https://eodata-s3keysmanager.dataspace.copernicus.eu/panel/s3-credentials
import os
import json
import requests
import boto3
from tqdm import tqdm
import time
import yaml
import argparse
import getpass
import sys
import logging
from pathlib import Path
from typing import Tuple, List, Optional
from botocore.exceptions import ClientError, NoCredentialsError


def load_credentials(file_name: str = 'secret.yml') -> Tuple[str, str]:
    """Load username and password from a YAML file or create the file if missing.

    If the file is not found, the user is prompted to input credentials, which are then saved.

    Args:
        file_name (str, optional): Name of the YAML file. Defaults to 'secret.yml'.

    Returns:
        tuple[str, str]: A tuple containing (username, password).

    Raises:
        yaml.YAMLError: If the YAML file is invalid or cannot be written properly.
        KeyError: If expected keys are missing in the YAML structure.
    """
    # First, check for secret.yml in the current working directory
    cwd_secrets_file_path = os.path.join(os.getcwd(), file_name)
    if os.path.isfile(cwd_secrets_file_path):
        secrets_file_path = cwd_secrets_file_path
    else:
        # Fallback: check for secret.yml in the script directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        secrets_file_path = os.path.join(script_dir, file_name)

    # Always prompt if not found, even in Jupyter or import context
    if not os.path.isfile(secrets_file_path):
        try:
            # For Jupyter, input and getpass work as expected
            print(f"Secrets file not found: {secrets_file_path}")
            username = input("Enter username: ").strip()
            password = getpass.getpass("Enter password: ").strip()
        except Exception as e:
            raise RuntimeError(f"Could not prompt for credentials: {e}")

        secrets = {
            'credentials': {
                'username': username,
                'password': password
            }
        }

        try:
            with open(secrets_file_path, 'w') as file:
                yaml.safe_dump(secrets, file)
            print(f"Secrets file created at: {secrets_file_path}")
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"Error writing secrets file: {e}")

    with open(secrets_file_path, 'r') as file:
        try:
            secrets = yaml.safe_load(file)
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"Invalid YAML format: {e}")

    try:
        username = secrets['credentials']['username']
        password = secrets['credentials']['password']
    except KeyError as e:
        raise KeyError(f"Missing expected key in secrets file: {e}")

    return username, password


# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')


def check_s3_permissions(s3_client, bucket_name: str, test_prefix: str) -> bool:
    """Check if we have the necessary S3 permissions before starting downloads.
    
    Args:
        s3_client: Boto3 S3 client object
        bucket_name: Name of the S3 bucket to test
        test_prefix: A prefix path to test access with
        
    Returns:
        bool: True if permissions are sufficient, False otherwise
    """
    try:
        # Test ListBucket permission
        response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=test_prefix, MaxKeys=1)
        logging.info(f'Successfully verified ListBucket permission for {bucket_name}')
        
        # Test HeadObject permission if objects exist
        if 'Contents' in response and response['Contents']:
            first_key = response['Contents'][0]['Key']
            s3_client.head_object(Bucket=bucket_name, Key=first_key)
            logging.info(f'Successfully verified HeadObject permission for {bucket_name}')
        
        return True
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        logging.error(f'S3 permission check failed: {error_code} - {error_message}')
        
        if error_code == '403':
            logging.error(f'Required S3 permissions: s3:ListBucket, s3:GetObject, s3:HeadObject')
            logging.error(f'Ensure your AWS credentials have access to bucket: {bucket_name}')
        
        return False
    except Exception as e:
        logging.error(f'Unexpected error during permission check: {str(e)}')
        return False


def download_s3_file_with_retry(s3_client, bucket_name: str, s3_key: str, 
                               local_path: str, max_retries: int = 3) -> bool:
    """Download a single file from S3 with retry logic and proper error handling.
    
    Args:
        s3_client: Boto3 S3 client object
        bucket_name: Name of the S3 bucket
        s3_key: S3 object key to download
        local_path: Local file path to save the download
        max_retries: Maximum number of retry attempts
        
    Returns:
        bool: True if download successful, False otherwise
    """
    assert max_retries > 0, 'max_retries must be greater than 0'
    
    for attempt in range(max_retries):
        try:
            # Ensure parent directory exists
            Path(local_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Check if file exists and get metadata
            try:
                head_response = s3_client.head_object(Bucket=bucket_name, Key=s3_key)
                file_size = head_response['ContentLength']
            except ClientError as e:
                error_code = e.response['Error']['Code']
                if error_code == '404':
                    logging.warning(f'File not found in S3: {s3_key}')
                    return False
                elif error_code == '403':
                    logging.error(f'Access denied for HeadObject on {s3_key}. Check s3:GetObject permissions.')
                    return False
                raise
            
            # Download the file with progress bar
            formatted_filename = format_filename(os.path.basename(local_path))
            progress_bar_format = (
                '{desc:.40}|{bar:20}| '
                '{percentage:3.0f}% {n_fmt}/{total_fmt}B'
            )
            
            with tqdm(total=file_size, unit='B', unit_scale=True,
                      desc=formatted_filename, ncols=80,
                      bar_format=progress_bar_format) as pbar:
                def progress_callback(bytes_transferred):
                    pbar.update(bytes_transferred)

                s3_client.download_file(bucket_name, s3_key, local_path, Callback=progress_callback)
            
            logging.debug(f'Successfully downloaded: {s3_key} -> {local_path}')
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            
            if error_code == '403':
                logging.error(f'Access denied downloading {s3_key}. Check your AWS credentials and s3:GetObject permissions.')
                return False
            elif error_code == '404':
                logging.warning(f'File not found: {s3_key}')
                return False
            else:
                logging.warning(f'Download attempt {attempt + 1} failed for {s3_key}: {error_code} - {error_message}')
                if attempt == max_retries - 1:
                    logging.error(f'Failed to download {s3_key} after {max_retries} attempts')
                    return False
                    
        except Exception as e:
            logging.warning(f'Download attempt {attempt + 1} failed for {s3_key}: {str(e)}')
            if attempt == max_retries - 1:
                logging.error(f'Failed to download {s3_key} after {max_retries} attempts due to unexpected error')
                return False
    
    return False


# Configuration parameters
config = {
    "auth_server_url": "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token",
    "odata_base_url": "https://catalogue.dataspace.copernicus.eu/odata/v1/Products",
    "s3_endpoint_url": "https://eodata.dataspace.copernicus.eu",
}


def get_access_token(config: dict, username: str, password: str) -> str:
    """Retrieve an access token from the authentication server.
    
    This token is used for subsequent API calls.
    Save the token to a file on the machine for reuse.
    
    Args:
        config (dict): Configuration dictionary containing auth server URL
        username (str): Username for authentication
        password (str): Password for authentication
        
    Returns:
        str: Access token for API authentication
        
    Raises:
        SystemExit: If token retrieval fails
    """
    token_file = os.path.expanduser('~/.eo_access_token')

    # Check if a valid token already exists
    if os.path.exists(token_file):
        with open(token_file, 'r') as file:
            token_data = json.load(file)
            if time.time() < token_data.get('expires_at', 0):
                print('Using cached access token.')
                print(f'Access token: {token_data["access_token"]}')
                return token_data['access_token']

    # Request a new token
    auth_data = {
        'client_id': 'cdse-public',
        'grant_type': 'password',
        'username': username,
        'password': password,
    }
    response = requests.post(config['auth_server_url'], data=auth_data, verify=True, allow_redirects=False)
    if response.status_code == 200:
        token_response = response.json()
        access_token = token_response['access_token']
        expires_in = token_response.get('expires_in', 3600)  # Default to 1 hour if not provided
        expires_at = time.time() + expires_in

        # Save the token to a file
        with open(token_file, 'w') as file:
            json.dump({'access_token': access_token, 'expires_at': expires_at}, file)

        print('Access token saved to disk.')
        return access_token
    else:
        print(f'Failed to retrieve access token. Status code: {response.status_code}')
        sys.exit(1)


def get_eo_product_details(config: dict, headers: dict, eo_product_name: str) -> Tuple[str, str]:
    """
    Retrieve EO product details using the OData API to determine the S3 path.
    
    Args:
        config (dict): Configuration dictionary containing API URLs
        headers (dict): HTTP headers for authentication
        eo_product_name (str): Name of the EO product to retrieve details for
        
    Returns:
        Tuple[str, str]: A tuple containing (product_id, s3_path)
        
    Raises:
        requests.exceptions.HTTPError: If the API request fails
        KeyError: If expected fields are missing from the response
        ValueError: If no products are found
    """
    odata_url = f"{config['odata_base_url']}?$filter=Name eq '{eo_product_name}'"
    logging.info(f'Querying product details from: {odata_url}')
    
    response = requests.get(odata_url, headers=headers)
    response.raise_for_status()
    
    response_data = response.json()
    
    if not response_data.get('value'):
        raise ValueError(f'No product found with name: {eo_product_name}')
    
    eo_product_data = response_data['value'][0]
    product_id = eo_product_data['Id']
    s3_path = eo_product_data['S3Path']
    
    logging.info(f'Product ID: {product_id}')
    logging.info(f'S3 Path: {s3_path}')
    
    return product_id, s3_path


def parse_s3_path(s3_path: str) -> Tuple[str, str]:
    """
    Parse S3 path to extract bucket name and object key.
    
    Args:
        s3_path (str): S3 path in format '/bucket/key' or 'bucket/key'
        
    Returns:
        Tuple[str, str]: A tuple containing (bucket_name, object_key)
        
    Raises:
        ValueError: If the S3 path format is invalid
    """
    if not s3_path:
        raise ValueError('S3 path cannot be empty')
    
    # Remove leading slash if present
    clean_path = s3_path.lstrip('/')
    
    if not clean_path:
        raise ValueError('S3 path cannot be just a slash')
    
    # Split into bucket and key
    path_parts = clean_path.split('/', 1)
    
    if len(path_parts) < 2:
        raise ValueError(f'Invalid S3 path format: {s3_path}. Expected format: /bucket/key or bucket/key')
    
    bucket_name = path_parts[0]
    object_key = path_parts[1]
    
    if not bucket_name:
        raise ValueError(f'Empty bucket name in S3 path: {s3_path}')
    
    if not object_key:
        raise ValueError(f'Empty object key in S3 path: {s3_path}')
    
    logging.info(f'Parsed S3 path - Bucket: {bucket_name}, Key: {object_key}')
    
    return bucket_name, object_key


def get_temporary_s3_credentials(headers: dict) -> dict:
    """
    Create temporary S3 credentials by calling the S3 keys manager API.
    
    Args:
        headers (dict): HTTP headers containing authorization token
        
    Returns:
        dict: Dictionary containing S3 credentials with keys 'access_id' and 'secret'
        
    Raises:
        requests.exceptions.HTTPError: If the API request fails
        SystemExit: If credential creation fails or max credentials reached
    """
    credentials_response = requests.post('https://s3-keys-manager.cloudferro.com/api/user/credentials', headers=headers)
    
    if credentials_response.status_code == 200:
        s3_credentials = credentials_response.json()
        logging.info('Temporary S3 credentials created successfully.')
        logging.info(f'Access ID: {s3_credentials["access_id"]}')
        logging.info(f'Secret (first 8 chars): {s3_credentials["secret"][:8]}...')
        return s3_credentials
    elif credentials_response.status_code == 403:
        response_body = credentials_response.json()
        if 'Max number of credentials reached' in response_body.get('detail', ''):
            logging.error('Error: Maximum number of temporary S3 credentials reached.')
            logging.error('Please delete unused credentials and try again.')
            logging.error('You can manage your credentials at: https://s3-keys-manager.cloudferro.com/')
        else:
            logging.error('Error: Access denied. Please check your permissions or access token.')
        logging.error(f'Response Body: {credentials_response.text}')
        sys.exit(1)
    else:
        logging.error(f'Failed to create temporary S3 credentials. Status code: {credentials_response.status_code}')
        logging.error(f'Response Body: {credentials_response.text}')
        sys.exit(1)


def create_s3_client_with_retry(config: dict, s3_credentials: dict, max_retries: int = 3) -> boto3.resource:
    """
    Create S3 client with retry logic and validation.
    
    Args:
        config (dict): Configuration dictionary containing S3 endpoint
        s3_credentials (dict): Dictionary containing S3 access credentials
        max_retries (int): Maximum number of retry attempts
        
    Returns:
        boto3.resource: Configured S3 resource
        
    Raises:
        ClientError: If S3 resource creation fails after all retries
    """
    for attempt in range(max_retries):
        try:
            logging.info(f'Creating S3 resource (attempt {attempt + 1}/{max_retries})')
            
            s3_resource = boto3.resource('s3',
                                       endpoint_url=config['s3_endpoint_url'],
                                       aws_access_key_id=s3_credentials['access_id'],
                                       aws_secret_access_key=s3_credentials['secret'],
                                       region_name='us-east-1')  # Add explicit region
            
            # Test the connection immediately
            s3_client = s3_resource.meta.client
            
            # Quick validation - try to list buckets or get service info
            try:
                # This should work even without specific bucket permissions
                s3_client.list_buckets()
                logging.info('S3 resource created and validated successfully')
                return s3_resource
            except ClientError as e:
                if e.response['Error']['Code'] == '403':
                    # This is expected - we may not have ListBuckets permission
                    # But if we can create the client, credentials are likely valid
                    logging.info('S3 resource created (ListBuckets not permitted but this is normal)')
                    return s3_resource
                else:
                    raise
                    
        except Exception as e:
            logging.warning(f'S3 resource creation attempt {attempt + 1} failed: {str(e)}')
            if attempt == max_retries - 1:
                logging.error(f'Failed to create S3 resource after {max_retries} attempts')
                raise
            time.sleep(2 ** attempt)  # Exponential backoff
    
    # This should never be reached, but just in case
    raise ClientError(
        error_response={'Error': {'Code': '500', 'Message': 'Failed to create S3 resource'}},
        operation_name='CreateS3Resource'
    )


def test_s3_connectivity(s3_resource, bucket_name: str) -> bool:
    """Test S3 connectivity and basic permissions.
    
    Args:
        s3_resource: Boto3 S3 resource object
        bucket_name: Name of the S3 bucket to test
        
    Returns:
        bool: True if connectivity is successful, False otherwise
    """
    try:
        # Try to list the bucket (this tests both connectivity and basic permissions)
        bucket = s3_resource.Bucket(bucket_name)
        list(bucket.objects.limit(1))  # Try to get at least one object
        logging.info(f'S3 connectivity test successful for bucket: {bucket_name}')
        return True
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == '403':
            logging.error(f'S3 access denied to bucket: {bucket_name}')
            logging.error('Please check your S3 credentials and permissions')
        elif error_code == '404':
            logging.error(f'S3 bucket not found: {bucket_name}')
        else:
            logging.error(f'S3 connectivity test failed: {error_code} - {e.response["Error"]["Message"]}')
        return False
    except Exception as e:
        logging.error(f'S3 connectivity test failed with unexpected error: {str(e)}')
        return False


def test_s3_connectivity_detailed(s3_resource, bucket_name: str) -> bool:
    """
    Test S3 connectivity with detailed debugging information.
    
    Args:
        s3_resource: Boto3 S3 resource object
        bucket_name (str): Name of the S3 bucket to test
        
    Returns:
        bool: True if connectivity is successful, False otherwise
    """
    try:
        logging.info(f'Testing S3 connectivity to bucket: {bucket_name}')
        logging.info(f'S3 endpoint: {s3_resource.meta.client._endpoint.host}')
        
        # Try to list the bucket with more specific error handling
        bucket = s3_resource.Bucket(bucket_name)
        
        # Test bucket access with a simple head_bucket operation first
        s3_client = s3_resource.meta.client
        logging.info('Testing bucket access with head_bucket...')
        s3_client.head_bucket(Bucket=bucket_name)
        logging.info('head_bucket successful')
        
        # Test listing objects
        logging.info('Testing object listing...')
        object_list = list(bucket.objects.limit(1))
        logging.info(f'Object listing successful, found {len(object_list)} objects (max 1)')
        
        logging.info(f'S3 connectivity test successful for bucket: {bucket_name}')
        return True
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        
        logging.error(f'S3 ClientError: {error_code} - {error_message}')
        
        if error_code == '403':
            logging.error(f'S3 access denied to bucket: {bucket_name}')
            logging.error('Possible causes:')
            logging.error('1. S3 credentials expired or invalid')
            logging.error('2. Account does not have S3 access enabled')
            logging.error('3. Bucket permissions are incorrect')
            logging.error('4. Network/firewall blocking S3 endpoint')
                
        elif error_code == '404':
            logging.error(f'S3 bucket not found: {bucket_name}')
        else:
            logging.error(f'S3 connectivity test failed: {error_code} - {error_message}')
            
        return False
        
    except Exception as e:
        logging.error(f'S3 connectivity test failed with unexpected error: {str(e)}')
        return False


def format_filename(filename, length=40):
    """
    Format a filename to a fixed length, truncating if necessary.
    """
    if len(filename) > length:
        return filename[:length - 3] + '...'
    else:
        return filename.ljust(length)


def download_file_s3(s3, bucket_name: str, s3_key: str, local_path: str, failed_downloads: List[str]) -> None:
    """Download a file from S3 with improved error handling.
    
    Args:
        s3: S3 client object
        bucket_name: Name of the S3 bucket
        s3_key: S3 object key to download
        local_path: Local file path to save the download
        failed_downloads: List to track failed downloads
    """
    if not download_s3_file_with_retry(s3, bucket_name, s3_key, local_path):
        failed_downloads.append(s3_key)


def traverse_and_download_s3(s3_resource, bucket_name: str, base_s3_path: str, 
                           local_path: str, failed_downloads: List[str]) -> None:
    """Traverse S3 bucket and download files with comprehensive error handling.
    
    Args:
        s3_resource: Boto3 S3 resource object
        bucket_name: Name of the S3 bucket
        base_s3_path: Base path in S3 bucket to traverse
        local_path: Local folder to download files to
        failed_downloads: List to track failed downloads
        
    Raises:
        ClientError: When S3 access is forbidden or other AWS errors occur
        NoCredentialsError: When AWS credentials are not configured
        AssertionError: When input parameters are invalid
    """
    assert bucket_name, 'bucket_name cannot be empty'
    assert base_s3_path, 'base_s3_path cannot be empty'
    assert local_path, 'local_path cannot be empty'
    
    try:
        # Create S3 client for better error handling
        s3_client = s3_resource.meta.client
        
        # Check permissions before starting
        if not check_s3_permissions(s3_client, bucket_name, base_s3_path):
            error_msg = f'Insufficient permissions to access S3 bucket: {bucket_name}'
            logging.error(error_msg)
            raise ClientError(
                error_response={'Error': {'Code': '403', 'Message': error_msg}},
                operation_name='PermissionCheck'
            )
        
        bucket = s3_resource.Bucket(bucket_name)
        files = bucket.objects.filter(Prefix=base_s3_path)
        
        downloaded_count = 0
        failed_count = 0
        
        for obj in files:
            s3_key = obj.key
            
            # Skip if it's a directory marker
            if s3_key.endswith('/'):
                continue
            
            # Create local file path
            relative_path = os.path.relpath(s3_key, base_s3_path)
            local_path_file = os.path.join(local_path, relative_path)
            local_dir = os.path.dirname(local_path_file)

            # Check if a file with the same name as the directory exists
            if os.path.isfile(local_dir):
                logging.info(f'Removing file to create directory: {local_dir}')
                os.remove(local_dir)

            # Create the directory if it doesn't exist
            os.makedirs(local_dir, exist_ok=True)

            # Download the file
            initial_failed_count = len(failed_downloads)
            download_file_s3(s3_client, bucket_name, s3_key, local_path_file, failed_downloads)
            
            if len(failed_downloads) > initial_failed_count:
                failed_count += 1
            else:
                downloaded_count += 1
        
        logging.info(f'Download summary: {downloaded_count} successful, {failed_count} failed')
        
    except NoCredentialsError:
        error_msg = 'AWS credentials not found. Please configure your credentials using "aws configure" or environment variables.'
        logging.error(error_msg)
        raise
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == '403':
            logging.error(f'Access denied to S3 bucket {bucket_name}. Required permissions: s3:ListBucket, s3:GetObject, s3:HeadObject')
        raise
    except Exception as e:
        logging.error(f'Unexpected error during S3 traversal: {str(e)}')
        raise


def check_s3_access_from_token(access_token: str) -> bool:
    """
    Check if the access token contains S3-related roles.
    
    Args:
        access_token (str): JWT access token from Copernicus
        
    Returns:
        bool: True if S3 access is likely available, False otherwise
    """
    try:
        import base64
        
        # Decode JWT payload (middle part)
        parts = access_token.split('.')
        if len(parts) != 3:
            return False
        
        # Add padding if needed
        payload = parts[1]
        payload += '=' * (4 - len(payload) % 4)
        
        decoded_bytes = base64.b64decode(payload)
        token_data = json.loads(decoded_bytes.decode('utf-8'))
        
        # Check for S3-related roles
        realm_access = token_data.get('realm_access', {})
        roles = realm_access.get('roles', [])
        
        s3_roles = ['s2-expert', 's3-access', 'copernicus-s3']
        has_s3_role = any(role in roles for role in s3_roles)
        
        logging.info(f'User roles: {roles}')
        logging.info(f'Has S3 access role: {has_s3_role}')
        
        return has_s3_role
        
    except Exception as e:
        logging.warning(f'Could not parse access token for S3 role check: {e}')
        return False


def download_via_odata_api(config: dict, headers: dict, product_name: str, local_folder: str) -> bool:
    """Download product using the OData API as fallback when S3 is not available.
    
    Args:
        config (dict): Configuration dictionary
        headers (dict): HTTP headers for authentication
        product_name (str): Name of the product to download
        local_folder (str): Local folder to save the download
        
    Returns:
        bool: True if download successful, False otherwise
    """
    try:
        logging.info('Attempting download via OData API (S3 fallback)')
        
        # Get product details
        eo_product_id, s3_path = get_eo_product_details(config, headers, product_name)
        
        # Construct download URL - use the correct download endpoint
        download_url = f'https://download.dataspace.copernicus.eu/Products({eo_product_id})/$value'
        
        logging.info(f'Downloading from: {download_url}')
        
        # Create local folder
        os.makedirs(local_folder, exist_ok=True)
        
        # Determine filename
        if product_name.endswith('.SAFE'):
            filename = f'{product_name}.zip'
        else:
            filename = f'{product_name}.zip'
        
        local_file_path = os.path.join(local_folder, filename)
        
        # Make request with proper headers and handle redirects
        session = requests.Session()
        session.headers.update(headers)
        
        # First make a HEAD request to check if authentication is working
        logging.info('Testing authentication with HEAD request...')
        head_response = session.head(download_url, allow_redirects=True)
        
        if head_response.status_code == 401:
            logging.error('Authentication failed - token may be expired or invalid')
            return False
        elif head_response.status_code == 403:
            logging.error('Access forbidden - insufficient permissions for download')
            return False
        elif head_response.status_code not in [200, 302]:
            logging.error(f'HEAD request failed with status: {head_response.status_code}')
            return False
            
        logging.info('Authentication test successful, starting download...')
        
        # Download with streaming and progress bar
        with session.get(download_url, stream=True, allow_redirects=True) as response:
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            
            with open(local_file_path, 'wb') as f:
                if total_size > 0:
                    with tqdm(total=total_size, unit='B', unit_scale=True,
                             desc=f'Downloading {filename}', ncols=80) as pbar:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                                pbar.update(len(chunk))
                else:
                    # No content-length header, download without progress bar
                    logging.info('No content-length header, downloading without progress tracking...')
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
        
        logging.info(f'Successfully downloaded to: {local_file_path}')
        return True
        
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            logging.error('Download failed: Authentication error (401 Unauthorized)')
            logging.error('Your access token may have expired or be invalid')
        elif e.response.status_code == 403:
            logging.error('Download failed: Access forbidden (403 Forbidden)')
            logging.error('You may not have permission to download this product')
        elif e.response.status_code == 404:
            logging.error('Download failed: Product not found (404 Not Found)')
        else:
            logging.error(f'OData API download failed with HTTP {e.response.status_code}: {str(e)}')
        return False
    except Exception as e:
        logging.error(f'OData API download failed: {str(e)}')
        return False


def pull_down(product_name: Optional[str] = None, args: Optional[argparse.Namespace] = None) -> None:
    """Main function to orchestrate the download process.
    
    Args:
        product_name (Optional[str]): Name of the Earth Observation product to download
        args (Optional[argparse.Namespace]): Command line arguments namespace
        
    Raises:
        ValueError: When product_name is not provided and args is None
        RuntimeError: When all download methods fail
    """
    if product_name is None:
        if args is None or not hasattr(args, 'eo_product_name') or args.eo_product_name is None:
            raise ValueError('product_name must be provided either directly or through args.eo_product_name')
        product_name = args.eo_product_name
    
    assert product_name is not None, 'product_name cannot be None at this point'
    
    logging.info(f'Starting download for product: {product_name}')

    # Step 1: Retrieve the access token
    if args is None:
        username, password = load_credentials()
        access_token = get_access_token(config, username, password)
    else:
        access_token = get_access_token(config, args.username, args.password)

    # Step 2: Set up headers for API calls
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Accept': 'application/json'
    }

    # Step 3: Check if S3 access is available from token
    has_s3_role = check_s3_access_from_token(access_token)
    
    if not has_s3_role:
        logging.info('S3 access not detected in token - using OData API download')
        
        if download_via_odata_api(config, headers, product_name, product_name):
            print('Product download complete via OData API.')
            return
        else:
            raise RuntimeError('OData API download failed - check authentication and permissions')

    # Step 4: Try S3 download path
    s3_credentials = None
    try:
        # Get EO product details (including S3 path)
        eo_product_id, s3_path = get_eo_product_details(config, headers, product_name)
        bucket_name, base_s3_path = parse_s3_path(s3_path)

        # Get temporary S3 credentials
        s3_credentials = get_temporary_s3_credentials(headers)

        # Set up S3 resource with simpler approach
        logging.info('Waiting 5 seconds for S3 credentials to propagate...')
        time.sleep(5)
        
        s3_resource = create_s3_resource_simple(config, s3_credentials)

        # Test basic connectivity
        try:
            bucket = s3_resource.Bucket(bucket_name)
            # Quick test to see if we can access the bucket
            list(bucket.objects.filter(Prefix=base_s3_path).limit(1))
            logging.info(f'S3 connectivity test successful for bucket: {bucket_name}')
        except ClientError as e:
            if e.response['Error']['Code'] == '403':
                logging.warning('S3 access denied - falling back to OData API download')
                raise Exception('S3 access denied, trying fallback')
            else:
                raise

        # Direct S3 download using simplified approach
        logging.info(f'Starting S3 download for: {base_s3_path}')
        
        if download_s3_product_direct(s3_resource, bucket_name, base_s3_path, product_name):
            print('Product download complete via S3.')
        else:
            print('Product download completed with some failures.')

    except Exception as e:
        logging.error(f'S3 download failed: {str(e)}')
        logging.info('Attempting OData API fallback...')
        
        # Try OData API as final fallback
        if download_via_odata_api(config, headers, product_name, product_name):
            print('Product download complete via OData API fallback.')
        else:
            raise RuntimeError('All download methods failed - check your credentials and permissions')
    
    finally:
        # Clean up temporary S3 credentials if they were created
        if s3_credentials:
            try:
                delete_url = f'https://s3-keys-manager.cloudferro.com/api/user/credentials/access_id/{s3_credentials["access_id"]}'
                delete_response = requests.delete(delete_url, headers=headers)
                if delete_response.status_code == 204:
                    print('Temporary S3 credentials deleted successfully.')
                else:
                    print(f'Failed to delete temporary S3 credentials. Status code: {delete_response.status_code}')
            except Exception as cleanup_error:
                logging.warning(f'Failed to cleanup S3 credentials: {cleanup_error}')


def main() -> None:
    """Main entry point for the downloader script."""
    # Set up command line argument parser
    parser = argparse.ArgumentParser(
        description="Script to download EO product using OData and S3 protocol.",
        epilog="Example usage: python -m phidown.downloader -u <username> -p <password> <eo_product_name>"
    )
    parser.add_argument('--init-secret', action='store_true', help='Prompt for credentials and create/overwrite secret.yml, then exit')
    # User credentials
    username, password = load_credentials()
    # Add command line arguments
    parser.add_argument('-u', '--username', type=str, default=username, help='Username for authentication')
    parser.add_argument('-p', '--password', type=str, default=password, help='Password for authentication')
    parser.add_argument('-eo_product_name', type=str, help='Name of the Earth Observation product to be downloaded (required)')
    args = parser.parse_args()

    if args.init_secret:
        # Force prompt and overwrite secret.yml using load_credentials
        try:
            username, password = load_credentials(file_name='secret.yml')
            print("Secrets file created/updated successfully.")
        except Exception as e:
            print(f"Error creating/updating secrets file: {e}")
            sys.exit(1)

    # Prompt for missing credentials
    if not args.username:
        args.username = input("Enter username: ")
    if not args.password:
        args.password = input("Enter password: ")

    pull_down(product_name=args.eo_product_name, args=args)
    sys.exit(0)


if __name__ == "__main__":
    main()
