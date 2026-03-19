from unittest.mock import Mock, patch

from phidown.search import CopernicusDataSearcher, REQUEST_TIMEOUT_SECONDS


@patch('phidown.search.requests.get')
def test_execute_query_uses_request_timeout(mock_get):
    mock_response = Mock()
    mock_response.raise_for_status = Mock()
    mock_response.json.return_value = {'@odata.count': 0, 'value': []}
    mock_get.return_value = mock_response

    searcher = CopernicusDataSearcher()
    searcher.query_by_filter(collection_name='SENTINEL-1')
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
    searcher.query_by_name('S1A_TEST_PRODUCT')

    assert mock_get.call_count == 1
    assert mock_get.call_args.kwargs['timeout'] == REQUEST_TIMEOUT_SECONDS

