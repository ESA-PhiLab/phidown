#!/usr/bin/env python3
# S3 Credentials: https://eodata-s3keysmanager.dataspace.copernicus.eu/panel/s3-credentials
import os
import json
import requests 
import boto3
from tqdm import tqdm
import time
import json
import yaml
import argparse
import sys 
import getpass

def load_credentials(file_name: str = 'secret.yml') -> tuple[str, str]:
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
    script_dir = os.path.dirname(os.path.abspath(__file__))
    secrets_file_path = os.path.join(script_dir, file_name)

    if not os.path.isfile(secrets_file_path):
        print(f"Secrets file not found: {secrets_file_path}")
        username = input("Enter username: ").strip()
        password = getpass.getpass("Enter password: ").strip()

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


# def load_credentials(file_name: str = 'secret.yml') -> tuple[str, str]:
#     """Load username and password from a YAML file located in the current script directory.

#     Args:
#         file_name (str, optional): Name of the YAML file. Defaults to 'secret.yml'.

#     Returns:
#         tuple[str, str]: A tuple containing (username, password).

#     Raises:
#         FileNotFoundError: If the secrets file does not exist.
#         KeyError: If expected keys are missing in the YAML structure.
#         yaml.YAMLError: If the YAML file is invalid.
#     """
#     script_dir = os.path.dirname(os.path.abspath(__file__))
#     secrets_file_path = os.path.join(script_dir, file_name)

#     if not os.path.isfile(secrets_file_path):
#         raise FileNotFoundError(f"Secrets file not found: {secrets_file_path}")

#     with open(secrets_file_path, 'r') as file:
#         try:
#             secrets = yaml.safe_load(file)
#         except yaml.YAMLError as e:
#             raise yaml.YAMLError(f"Invalid YAML format: {e}")

#     try:
#         username = secrets['credentials']['username']
#         password = secrets['credentials']['password']
#     except KeyError as e:
#         raise KeyError(f"Missing expected key in secrets file: {e}")

#     return username, password



# Configuration parameters
config = {
    "auth_server_url": "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token",
    "odata_base_url": "https://catalogue.dataspace.copernicus.eu/odata/v1/Products",
    "s3_endpoint_url": "https://eodata.dataspace.copernicus.eu",
}

def get_access_token(config, username, password):
    """
    Retrieve an access token from the authentication server.
    This token is used for subsequent API calls.
    Save the token to a file on the machine for reuse.
    """
    token_file = os.path.expanduser("~/.eo_access_token")

    # Check if a valid token already exists
    if os.path.exists(token_file):
        with open(token_file, "r") as file:
            token_data = json.load(file)
            if time.time() < token_data.get("expires_at", 0):
                print("Using cached access token.")
                print(f"Access token: {token_data['access_token']}")
                return token_data["access_token"]

    # Request a new token
    auth_data = {
        "client_id": "cdse-public",
        "grant_type": "password",
        "username": username,
        "password": password,
    }
    response = requests.post(config["auth_server_url"], data=auth_data, verify=True, allow_redirects=False)
    if response.status_code == 200:
        token_response = response.json()
        access_token = token_response["access_token"]
        expires_in = token_response.get("expires_in", 3600)  # Default to 1 hour if not provided
        expires_at = time.time() + expires_in

        # Save the token to a file
        with open(token_file, "w") as file:
            json.dump({"access_token": access_token, "expires_at": expires_at}, file)

        print("Access token saved to disk.")
        return access_token
    else:
        print(f"Failed to retrieve access token. Status code: {response.status_code}")
        exit(1)


def get_eo_product_details(config, headers, eo_product_name):
    """
    Retrieve EO product details using the OData API to determine the S3 path.
    """
    odata_url = f"{config['odata_base_url']}?$filter=Name eq '{eo_product_name}'"
    response = requests.get(odata_url, headers=headers)
    if response.status_code == 200:
        eo_product_data = response.json()["value"][0]
        return eo_product_data["Id"], eo_product_data["S3Path"]
    else:
        print(f"Failed to retrieve EO product details. Status code: {response.status_code}")
        exit(1)


def get_temporary_s3_credentials(headers):
    """
    Create temporary S3 credentials by calling the S3 keys manager API.
    """
    credentials_response = requests.post("https://s3-keys-manager.cloudferro.com/api/user/credentials", headers=headers)
    if credentials_response.status_code == 200:
        s3_credentials = credentials_response.json()
        print("Temporary S3 credentials created successfully.")
        print(f"access: {s3_credentials['access_id']}")
        print(f"secret: {s3_credentials['secret']}")
        return s3_credentials
    elif credentials_response.status_code == 403:
        response_body = credentials_response.json()
        if "Max number of credentials reached" in response_body.get("detail", ""):
            print("Error: Maximum number of temporary S3 credentials reached.")
            print("Please delete unused credentials and try again.")
        else:
            print("Error: Access denied. Please check your permissions or access token.")
        print(f"Response Body: {credentials_response.text}")
        exit(1)
    else:
        print(f"Failed to create temporary S3 credentials. Status code: {credentials_response.status_code}")
        print(f"Response Body: {credentials_response.text}")
        exit(1)


def format_filename(filename, length=40):
    """
    Format a filename to a fixed length, truncating if necessary.
    """
    if len(filename) > length:
        return filename[:length - 3] + '...'
    else:
        return filename.ljust(length)


def download_file_s3(s3, bucket_name, s3_key, local_path, failed_downloads):
    """
    Download a file from S3 with a progress bar.
    Track failed downloads in a list.
    """
    try:
        file_size = s3.head_object(Bucket=bucket_name, Key=s3_key)['ContentLength']
        formatted_filename = format_filename(os.path.basename(local_path))
        with tqdm(total=file_size, unit='B', unit_scale=True, desc=formatted_filename, ncols=80, bar_format='{desc:.40}|{bar:20}| {percentage:3.0f}% {n_fmt}/{total_fmt}B') as pbar:
            def progress_callback(bytes_transferred):
                pbar.update(bytes_transferred)

            s3.download_file(bucket_name, s3_key, local_path, Callback=progress_callback)
    except Exception as e:
        print(f"Failed to download {s3_key}. Error: {e}")
        failed_downloads.append(s3_key)


def traverse_and_download_s3(s3_resource, bucket_name, base_s3_path, local_path, failed_downloads):
    """
    Traverse the S3 bucket and download all files under the specified prefix.
    """
    bucket = s3_resource.Bucket(bucket_name)
    files = bucket.objects.filter(Prefix=base_s3_path)

    for obj in files:
        s3_key = obj.key
        relative_path = os.path.relpath(s3_key, base_s3_path)
        local_path_file = os.path.join(local_path, relative_path)
        local_dir = os.path.dirname(local_path_file)

        # Check if a file with the same name as the directory exists
        if os.path.isfile(local_dir):
            print(f"Creating a directory: {local_dir}")
            os.remove(local_dir)

        # Create the directory if it doesn't exist
        os.makedirs(local_dir, exist_ok=True)

        # Download the file
        download_file_s3(s3_resource.meta.client, bucket_name, s3_key, local_path_file, failed_downloads)


def pull_down(product_name=None, args=None):
    """
    Main function to orchestrate the download process.
    """
    if product_name is None:
        product_name = args.eo_product_name
    
    # Step 1: Retrieve the access token
    if args is None:
        # Usage example
        username, password = load_credentials()
        access_token = get_access_token(config, username, password)
    else:
        access_token = get_access_token(config, args.username, args.password)

    # Step 2: Set up headers for API calls
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }

    # Step 3: Get EO product details (including S3 path)
    eo_product_id, s3_path = get_eo_product_details(config, headers, product_name)
    bucket_name, base_s3_path = s3_path.lstrip('/').split('/', 1)

    # Step 4: Get temporary S3 credentials
    s3_credentials = get_temporary_s3_credentials(headers)

    # Step 5: Set up S3 client and resource with temporary credentials
    time.sleep(5)  # Ensure the key pair is installed
    s3_resource = boto3.resource('s3',
                                 endpoint_url=config["s3_endpoint_url"],
                                 aws_access_key_id=s3_credentials["access_id"],
                                 aws_secret_access_key=s3_credentials["secret"])

    # Step 6: Create the top-level folder and start download
    top_level_folder = product_name
    os.makedirs(top_level_folder, exist_ok=True)
    failed_downloads = []
    traverse_and_download_s3(s3_resource, bucket_name, base_s3_path, top_level_folder, failed_downloads)

    # Step 7: Print final status
    if not failed_downloads:
        print("Product download complete.")
    else:
        print("Product download incomplete:")
        for failed_file in failed_downloads:
            print(f"- {failed_file}")

    # Step 7: Delete the temporary S3 credentials
    delete_response = requests.delete(f"https://s3-keys-manager.cloudferro.com/api/user/credentials/access_id/{s3_credentials['access_id']}", headers=headers)
    if delete_response.status_code == 204:
        print("Temporary S3 credentials deleted successfully.")
    else:
        print(f"Failed to delete temporary S3 credentials. Status code: {delete_response.status_code}")

if __name__ == "__main__":
    
    # Set up command line argument parser
    parser = argparse.ArgumentParser(
        description="Script to download EO product using OData and S3 protocol.",
        epilog="Example usage: python script.py -u <username> -p <password> <eo_product_name>"
    )
    # User credentials
    username, password = load_credentials()
    # Add command line arguments
    parser.add_argument('-u', '--username', type=str, default=username, help='Username for authentication')
    parser.add_argument('-p', '--password', type=str, default=password, help='Password for authentication')
    parser.add_argument('-eo_product_name', type=str, help='Name of the Earth Observation product to be downloaded (required)')
    args = parser.parse_args()

    # Prompt for missing credentials
    if not args.username:
        args.username = input("Enter username: ")
    if not args.password:
        args.password = input("Enter password: ")
    
    pull_down(product_name=args.eo_product_name, args=args)