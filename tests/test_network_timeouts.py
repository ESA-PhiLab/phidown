from unittest.mock import Mock, patch

from phidown.search import CopernicusDataSearcher, REQUEST_TIMEOUT_SECONDS


@patch('phidown.search.requests.get')
def test_execute_query_uses_request_timeout(mock_get):
    # Product search uses STAC; burst search still uses OData GET requests.
    mock_response = Mock()
    mock_response.raise_for_status = Mock()
    mock_response.json.return_value = {'@odata.count': 0, 'value': []}
    mock_get.return_value = mock_response

    searcher = CopernicusDataSearcher()
    searcher.query_by_filter(collection_name='SENTINEL-1', burst_mode=True, swath_identifier='IW1')
    searcher.execute_query()

    assert mock_get.call_count == 1
    assert mock_get.call_args.kwargs['timeout'] == REQUEST_TIMEOUT_SECONDS


@patch('phidown.search.requests.get')
def test_query_by_name_uses_request_timeout(mock_get):
    mock_response = Mock()
    mock_response.raise_for_status = Mock()
    mock_response.json.return_value = {'value': []}
    mock_get.return_value = mock_response

    searcher = CopernicusDataSearcher()
    searcher.burst_mode = True
    searcher.query_by_name('S1A_TEST_PRODUCT')

    assert mock_get.call_count == 1
    assert mock_get.call_args.kwargs['timeout'] == REQUEST_TIMEOUT_SECONDS



@patch('phidown.stac.requests.post')
@patch('phidown.stac.requests.get')
def test_stac_product_search_uses_request_timeout(mock_get, mock_post):
    collections = Mock()
    collections.raise_for_status = Mock()
    collections.json.return_value = {'collections': [{'id': 'sentinel-1-grd'}], 'links': []}
    mock_get.return_value = collections
    search = Mock()
    search.raise_for_status = Mock()
    search.json.return_value = {'features': [], 'links': []}
    mock_post.return_value = search

    searcher = CopernicusDataSearcher()
    searcher.query_by_filter(collection_name='SENTINEL-1')
    searcher.execute_query()
    searcher.query_by_name('S1A_TEST_PRODUCT')

    assert mock_get.call_args.kwargs['timeout'] == REQUEST_TIMEOUT_SECONDS
    assert all(call.kwargs['timeout'] == REQUEST_TIMEOUT_SECONDS for call in mock_post.call_args_list)
