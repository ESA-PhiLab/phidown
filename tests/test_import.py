import os
import pytest
from unittest import mock
import tempfile
import json

import phidown
from phidown.downloader import load_credentials
from phidown.search import CopernicusDataSearcher


def test_load_credentials_file_not_found():
    with pytest.raises(FileNotFoundError):
        load_credentials("nonexistent_file.json")


def test_load_credentials_valid_file():
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp:
        credentials = {"username": "test_user", "password": "test_pass"}
        json.dump(credentials, temp)
    
    try:
        result = load_credentials(temp.name)
        assert result == credentials
    finally:
        os.unlink(temp.name)


@mock.patch('phidown.search.requests.get')
def test_copernicus_data_searcher_search(mock_get):
    # Mock response
    mock_response = mock.Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"products": [{"id": "test_id", "name": "test_product"}]}
    mock_get.return_value = mock_response
    
    # Create searcher and perform search
    searcher = CopernicusDataSearcher(credentials={"username": "test", "password": "test"})
    results = searcher.search(query="test query")
    
    # Verify results
    assert len(results) == 1
    assert results[0]["id"] == "test_id"
    assert mock_get.called


@mock.patch('phidown.search.requests.get')
def test_copernicus_data_searcher_error_response(mock_get):
    # Mock error response
    mock_response = mock.Mock()
    mock_response.status_code = 401
    mock_get.return_value = mock_response
    
    # Create searcher and test error handling
    searcher = CopernicusDataSearcher(credentials={"username": "test", "password": "test"})
    with pytest.raises(Exception):  # Adjust to the specific exception your code raises
        searcher.search(query="test query")
