import pytest
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from phidown.search import CopernicusDataSearcher
from unittest.mock import Mock, patch
import pandas as pd

# Define the path to the config file relative to the test file
CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', 'phidown', 'config.json')


def test_pagination_disabled_by_default():
    """Test that pagination is not triggered when count=False"""
    searcher = CopernicusDataSearcher()
    searcher.query_by_filter(
        collection_name='SENTINEL-1',
        product_type='SLC',
        top=10,
        count=False  # Pagination should not trigger
    )
    
    # Mock response with large count
    mock_response = Mock()
    mock_response.json.return_value = {
        'value': [{'Id': f'product_{i}', 'Name': f'name_{i}'} for i in range(10)],
        '@odata.count': 1500  # More than top=10, but count=False
    }
    mock_response.raise_for_status = Mock()
    
    with patch('requests.get', return_value=mock_response) as mock_get:
        df = searcher.execute_query()
        
    # Should only make one request since count=False
    assert mock_get.call_count == 1
    assert len(df) == 10  # Only the first page


def test_pagination_when_count_enabled_and_results_exceed_top():
    """Test pagination is triggered when count=True and results > top"""
    searcher = CopernicusDataSearcher()
    searcher.query_by_filter(
        collection_name='SENTINEL-1',
        product_type='SLC',
        top=5,
        count=True
    )
    
    # Mock responses for pagination
    mock_response_1 = Mock()
    mock_response_1.json.return_value = {
        'value': [{'Id': f'product_{i}', 'Name': f'name_{i}'} for i in range(5)],
        '@odata.count': 12
    }
    mock_response_1.raise_for_status = Mock()
    
    mock_response_2 = Mock()
    mock_response_2.json.return_value = {
        'value': [{'Id': f'product_{i}', 'Name': f'name_{i}'} for i in range(5, 10)]
    }
    mock_response_2.raise_for_status = Mock()
    
    mock_response_3 = Mock()
    mock_response_3.json.return_value = {
        'value': [{'Id': f'product_{i}', 'Name': f'name_{i}'} for i in range(10, 12)]
    }
    mock_response_3.raise_for_status = Mock()
    
    with patch('requests.get', side_effect=[mock_response_1, mock_response_2, mock_response_3]) as mock_get:
        df = searcher.execute_query()
        
    # Should make 3 requests total
    assert mock_get.call_count == 3
    assert len(df) == 12
    
    # Check that skip parameters were used correctly
    calls = mock_get.call_args_list
    assert '$skip=5' in calls[1][0][0]
    assert '$skip=10' in calls[2][0][0]


def test_no_pagination_when_results_within_top_limit():
    """Test no pagination when count=True but results <= top"""
    searcher = CopernicusDataSearcher()
    searcher.query_by_filter(
        collection_name='SENTINEL-1',
        product_type='SLC',
        top=100,
        count=True
    )
    
    # Mock response with count less than top
    mock_response = Mock()
    mock_response.json.return_value = {
        'value': [{'Id': f'product_{i}', 'Name': f'name_{i}'} for i in range(50)],
        '@odata.count': 50  # Less than top=100
    }
    mock_response.raise_for_status = Mock()
    
    with patch('requests.get', return_value=mock_response) as mock_get:
        df = searcher.execute_query()
        
    # Should only make one request
    assert mock_get.call_count == 1
    assert len(df) == 50


def test_pagination_with_1000_page_size():
    """Test pagination with default page size of 1000"""
    searcher = CopernicusDataSearcher()
    searcher.query_by_filter(
        collection_name='SENTINEL-1',
        product_type='SLC',
        top=1000,  # Default page size
        count=True
    )
    
    # Mock responses for large dataset
    mock_response_1 = Mock()
    mock_response_1.json.return_value = {
        'value': [{'Id': f'product_{i}', 'Name': f'name_{i}'} for i in range(1000)],
        '@odata.count': 2500
    }
    mock_response_1.raise_for_status = Mock()
    
    mock_response_2 = Mock()
    mock_response_2.json.return_value = {
        'value': [{'Id': f'product_{i}', 'Name': f'name_{i}'} for i in range(1000, 2000)]
    }
    mock_response_2.raise_for_status = Mock()
    
    mock_response_3 = Mock()
    mock_response_3.json.return_value = {
        'value': [{'Id': f'product_{i}', 'Name': f'name_{i}'} for i in range(2000, 2500)]
    }
    mock_response_3.raise_for_status = Mock()
    
    with patch('requests.get', side_effect=[mock_response_1, mock_response_2, mock_response_3]) as mock_get:
        df = searcher.execute_query()
        
    # Should make 3 requests total
    assert mock_get.call_count == 3
    assert len(df) == 2500
    
    # Check skip parameters
    calls = mock_get.call_args_list
    assert '$skip=1000' in calls[1][0][0]
    assert '$skip=2000' in calls[2][0][0]


def test_pagination_handles_request_errors_gracefully():
    """Test that pagination handles request errors gracefully"""
    searcher = CopernicusDataSearcher()
    searcher.query_by_filter(
        collection_name='SENTINEL-1',
        product_type='SLC',
        top=5,
        count=True
    )
    
    # Mock first response successful
    mock_response_1 = Mock()
    mock_response_1.json.return_value = {
        'value': [{'Id': f'product_{i}', 'Name': f'name_{i}'} for i in range(5)],
        '@odata.count': 15
    }
    mock_response_1.raise_for_status = Mock()
    
    # Mock second response fails
    mock_response_2 = Mock()
    mock_response_2.raise_for_status.side_effect = Exception("Network error")
    
    with patch('requests.get', side_effect=[mock_response_1, mock_response_2]):
        # Should not raise exception, but return partial results
        df = searcher.execute_query()
        
    # Should return at least the first page
    assert len(df) == 5
    assert 'product_0' in df['Id'].values