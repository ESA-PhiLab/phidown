import pytest

from phidown.search import CopernicusDataSearcher


def test_validate_time_allows_equivalent_aware_instants():
    searcher = CopernicusDataSearcher()
    # Same instant in different offsets
    searcher.query_by_filter(
        collection_name='SENTINEL-1',
        start_date='2024-01-01T00:00:00+01:00',
        end_date='2023-12-31T23:00:00+00:00',
    )


def test_validate_time_rejects_later_start_datetime():
    searcher = CopernicusDataSearcher()
    with pytest.raises(ValueError, match='start_date must not be later than end_date'):
        searcher.query_by_filter(
            collection_name='SENTINEL-1',
            start_date='2024-01-01T00:00:01+00:00',
            end_date='2024-01-01T00:00:00+00:00',
        )


def test_validate_time_rejects_mixed_timezone_awareness():
    searcher = CopernicusDataSearcher()
    with pytest.raises(ValueError, match='timezone-aware or both be timezone-naive'):
        searcher.query_by_filter(
            collection_name='SENTINEL-1',
            start_date='2024-01-01T00:00:00+00:00',
            end_date='2024-01-01T00:00:00',
        )


def test_validate_time_keeps_existing_iso_examples():
    searcher = CopernicusDataSearcher()
    searcher.query_by_filter(
        collection_name='SENTINEL-1',
        start_date='2023-01-01T00:00:00',
        end_date='2023-01-31T23:59:59',
    )

