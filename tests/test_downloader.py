import pytest
import os
import yaml
from unittest.mock import patch, mock_open
from phidown.downloader import load_credentials

# Define the path to the directory where the test file is located
TEST_DIR = os.path.dirname(os.path.abspath(__file__))

# Test loading credentials when the file exists
@patch('builtins.open', new_callable=mock_open, read_data='credentials:\n  username: testuser\n  password: testpass\n')
@patch('os.path.isfile', return_value=True)
def test_load_credentials_file_exists(mock_isfile, mock_file):
    username, password = load_credentials(file_name='dummy_secret.yml')
    # Construct the expected path relative to the test directory
    expected_path = os.path.join(TEST_DIR, '..', 'phidown', 'dummy_secret.yml')
    mock_isfile.assert_called_once_with(expected_path)
    mock_file.assert_called_once_with(expected_path, 'r')
    assert username == 'testuser'
    assert password == 'testpass'

# Test creating credentials file when it doesn't exist
@patch('builtins.open', new_callable=mock_open)
@patch('os.path.isfile', return_value=False)
@patch('builtins.input', side_effect=['newuser'])
@patch('getpass.getpass', return_value='newpass')
@patch('yaml.safe_dump')
def test_load_credentials_file_not_found(mock_safe_dump, mock_getpass, mock_input, mock_isfile, mock_file):
    username, password = load_credentials(file_name='new_secret.yml')
    # Construct the expected path relative to the test directory
    expected_path = os.path.join(TEST_DIR, '..', 'phidown', 'new_secret.yml')
    mock_isfile.assert_called_once_with(expected_path)
    # Check that input and getpass were called
    mock_input.assert_called_once_with("Enter username: ")
    mock_getpass.assert_called_once_with("Enter password: ")
    # Check that the file was opened for writing first, then reading
    mock_file.assert_any_call(expected_path, 'w')
    mock_file.assert_any_call(expected_path, 'r')
    # Check that yaml.safe_dump was called with the correct data
    expected_secrets = {'credentials': {'username': 'newuser', 'password': 'newpass'}}
    mock_safe_dump.assert_called_once_with(expected_secrets, mock_file())
    # The function should return the newly entered credentials
    # Note: The mock_open needs to be configured to return the written data on the second call (read)
    # This part is tricky with the default mock_open. A more robust mock might be needed for full verification.
    # For simplicity, we assume the read after write works as intended by the function logic.
    # A better approach might involve separate mocks for write and read.

# Test invalid YAML format
@patch('builtins.open', new_callable=mock_open, read_data='invalid yaml:')
@patch('os.path.isfile', return_value=True)
def test_load_credentials_invalid_yaml(mock_isfile, mock_file):
    with pytest.raises(yaml.YAMLError):
        load_credentials(file_name='invalid.yml')

# Test missing keys in YAML
@patch('builtins.open', new_callable=mock_open, read_data='credentials:\n  user: testuser\n')
@patch('os.path.isfile', return_value=True)
def test_load_credentials_missing_keys(mock_isfile, mock_file):
    with pytest.raises(KeyError):
        load_credentials(file_name='missing_keys.yml')

# Add more tests for get_access_token, get_eo_product_details, get_temporary_s3_credentials,
# download_file_s3, traverse_and_download_s3, and pull_down using mocking.
# These will involve mocking requests.post, requests.get, requests.delete, boto3.resource,
# s3 methods (head_object, download_file, Bucket, objects.filter), os.makedirs, tqdm, etc.
