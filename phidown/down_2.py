import os
import time
import logging
import requests
import boto3
from botocore.exceptions import ClientError
from tqdm import tqdm

# ...existing functions...

def download_s3_product_direct(s3_resource, bucket_name: str, product_prefix: str, target_dir: str = '') -> bool:
    """
    Downloads every file in bucket with provided product as prefix using direct approach.
    
    Args:
        s3_resource: Boto3 S3 resource object
        bucket_name (str): Name of the S3 bucket  
        product_prefix (str): S3 prefix/path to the product
        target_dir (str): Local directory for downloaded files. Defaults to current directory.
        
    Returns:
        bool: True if download successful, False otherwise
        
    Raises:
        FileNotFoundError: If no files found for the product prefix
    """
    try:
        bucket = s3_resource.Bucket(bucket_name)
        files = list(bucket.objects.filter(Prefix=product_prefix))
        
        if not files:
            raise FileNotFoundError(f'Could not find any files for {product_prefix}')
        
        logging.info(f'Found {len(files)} files to download')
        
        successful_downloads = 0
        failed_downloads = []
        
        for file_obj in files:
            # Skip directory markers
            if file_obj.key.endswith('/'):
                continue
                
            local_file_path = os.path.join(target_dir, file_obj.key)
            local_dir = os.path.dirname(local_file_path)
            
            # Ensure directory exists
            os.makedirs(local_dir, exist_ok=True)
            
            # Skip if it's a directory
            if os.path.isdir(local_file_path):
                continue
                
            try:
                # Get file size for progress tracking
                file_size = file_obj.size
                formatted_filename = format_filename(os.path.basename(file_obj.key))
                
                # Download with progress bar
                with tqdm(total=file_size, unit='B', unit_scale=True,
                         desc=formatted_filename, ncols=80) as pbar:
                    def progress_callback(bytes_transferred):
                        pbar.update(bytes_transferred)
                    
                    bucket.download_file(file_obj.key, local_file_path, Callback=progress_callback)
                
                successful_downloads += 1
                logging.debug(f'Successfully downloaded: {file_obj.key}')
                
            except Exception as e:
                logging.error(f'Failed to download {file_obj.key}: {str(e)}')
                failed_downloads.append(file_obj.key)
        
        logging.info(f'Download completed: {successful_downloads} successful, {len(failed_downloads)} failed')
        
        if failed_downloads:
            logging.warning(f'Failed downloads: {failed_downloads}')
            return False
        
        return True
        
    except Exception as e:
        logging.error(f'S3 direct download failed: {str(e)}')
        return False

def create_s3_resource_simple(config: dict, s3_credentials: dict) -> boto3.resource:
    """
    Create S3 resource using the simpler approach.
    
    Args:
        config (dict): Configuration dictionary containing S3 endpoint
        s3_credentials (dict): Dictionary containing S3 access credentials
        
    Returns:
        boto3.resource: Configured S3 resource
    """
    return boto3.resource(
        's3',
        endpoint_url=config['s3_endpoint_url'],
        aws_access_key_id=s3_credentials['access_id'],
        aws_secret_access_key=s3_credentials['secret'],
        region_name='default'  # Use 'default' instead of 'us-east-1'
    )

def pull_down(product_name: Optional[str] = None, args: Optional[argparse.Namespace] = None) -> None:
    """
    Main function to orchestrate the download process.
    
    Args:
        product_name (Optional[str]): Name of the Earth Observation product to download
        args (Optional[argparse.Namespace]): Command line arguments namespace
        
    Raises:
        ValueError: When product_name is not provided and args is None
        RuntimeError: When both S3 and OData API downloads fail
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
        top_level_folder = product_name
        
        if download_via_odata_api(config, headers, product_name, top_level_folder):
            print('Product download complete via OData API.')
            return
        else:
            raise RuntimeError('OData API download failed')

    # Step 4: Try S3 download path with simplified approach
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
                
                # Clean up credentials and try fallback
                try:
                    delete_url = f'https://s3-keys-manager.cloudferro.com/api/user/credentials/access_id/{s3_credentials["access_id"]}'
                    requests.delete(delete_url, headers=headers)
                except Exception:
                    pass
                
                if download_via_odata_api(config, headers, product_name, product_name):
                    print('Product download complete via OData API fallback.')
                    return
                else:
                    raise RuntimeError('Both S3 and OData API downloads failed')
            else:
                raise

        # Direct S3 download using simplified approach
        logging.info(f'Starting S3 download for: {base_s3_path}')
        
        if download_s3_product_direct(s3_resource, bucket_name, base_s3_path, product_name):
            print('Product download complete via S3.')
        else:
            print('Product download completed with some failures.')

        # Clean up temporary S3 credentials
        delete_url = f'https://s3-keys-manager.cloudferro.com/api/user/credentials/access_id/{s3_credentials["access_id"]}'
        delete_response = requests.delete(delete_url, headers=headers)
        if delete_response.status_code == 204:
            print('Temporary S3 credentials deleted successfully.')
        else:
            print(f'Failed to delete temporary S3 credentials. Status code: {delete_response.status_code}')

    except Exception as e:
        logging.error(f'S3 download failed: {str(e)}')
        logging.info('Attempting OData API fallback...')
        
        # Try OData API as final fallback
        if download_via_odata_api(config, headers, product_name, product_name):
            print('Product download complete via OData API fallback.')
        else:
            raise RuntimeError(f'All download methods failed. Last error: {str(e)}')

# ...existing code...