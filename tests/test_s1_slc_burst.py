"""
Tests for Sentinel-1 SLC/Burst Downloader functionality.

This module contains tests for the S1 SLC/Burst download functionality
integrated into CopernicusDataSearcher, including coverage calculation,
orbit optimization, temporal statistics, and download capabilities.
"""

import pytest
import sys
import os
import json
import tempfile
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
import numpy as np

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from phidown.search import CopernicusDataSearcher


class TestAOICoverage:
    """Tests for AOI coverage calculation."""
    
    def test_centroid_calculation_simple_polygon(self):
        """Test centroid calculation for a simple polygon."""
        searcher = CopernicusDataSearcher()
        aoi = 'POLYGON((10.0 45.0, 12.0 45.0, 12.0 47.0, 10.0 47.0, 10.0 45.0))'
        
        lon, lat = searcher._get_aoi_centroid(aoi)
        
        assert abs(lon - 11.0) < 0.1
        assert abs(lat - 46.0) < 0.1
    
    def test_centroid_calculation_with_stored_aoi(self):
        """Test centroid calculation using stored AOI."""
        searcher = CopernicusDataSearcher()
        searcher.aoi_wkt = 'POLYGON((10.0 45.0, 12.0 45.0, 12.0 47.0, 10.0 47.0, 10.0 45.0))'
        
        lon, lat = searcher._get_aoi_centroid()
        
        assert abs(lon - 11.0) < 0.1
        assert abs(lat - 46.0) < 0.1
    
    def test_centroid_missing_aoi_raises_error(self):
        """Test that missing AOI raises ValueError."""
        searcher = CopernicusDataSearcher()
        
        with pytest.raises(ValueError, match='AOI WKT is not set'):
            searcher._get_aoi_centroid()
    
    def test_centroid_invalid_wkt_raises_error(self):
        """Test that invalid WKT raises ValueError."""
        searcher = CopernicusDataSearcher()
        
        with pytest.raises(ValueError):
            searcher._get_aoi_centroid('INVALID WKT')


class TestOrbitDirectionRecommendation:
    """Tests for regional orbit direction recommendations."""
    
    def test_europe_region_recommends_descending(self):
        """Test that European AOI recommends descending orbit."""
        searcher = CopernicusDataSearcher()
        # Rome, Italy (12.5, 41.9)
        aoi = 'POLYGON((11.0 41.0, 14.0 41.0, 14.0 43.0, 11.0 43.0, 11.0 41.0))'
        
        direction = searcher._get_recommended_orbit_direction(aoi)
        
        assert direction == 'DESCENDING'
    
    def test_america_region_recommends_descending(self):
        """Test that American AOI recommends descending orbit."""
        searcher = CopernicusDataSearcher()
        # New York area (-74, 40.7)
        aoi = 'POLYGON((-75.0 40.0, -73.0 40.0, -73.0 42.0, -75.0 42.0, -75.0 40.0))'
        
        direction = searcher._get_recommended_orbit_direction(aoi)
        
        assert direction == 'DESCENDING'
    
    def test_asia_region_recommends_ascending(self):
        """Test that Asian AOI recommends ascending orbit."""
        searcher = CopernicusDataSearcher()
        # Tokyo area (139.7, 35.7)
        aoi = 'POLYGON((138.0 35.0, 141.0 35.0, 141.0 37.0, 138.0 37.0, 138.0 35.0))'
        
        direction = searcher._get_recommended_orbit_direction(aoi)
        
        assert direction == 'ASCENDING'
    
    def test_australia_region_recommends_ascending(self):
        """Test that Australian AOI recommends ascending orbit."""
        searcher = CopernicusDataSearcher()
        # Sydney area (151.2, -33.9)
        aoi = 'POLYGON((150.0 -35.0, 152.0 -35.0, 152.0 -33.0, 150.0 -33.0, 150.0 -35.0))'
        
        direction = searcher._get_recommended_orbit_direction(aoi)
        
        assert direction == 'ASCENDING'


class TestSubswathPriority:
    """Tests for subswath priority ordering."""
    
    def test_subswath_priority_constants(self):
        """Test that subswath priority constants are correct."""
        searcher = CopernicusDataSearcher()
        
        assert searcher._SUBSWATH_PRIORITY['IW1'] == 0
        assert searcher._SUBSWATH_PRIORITY['IW2'] == 1
        assert searcher._SUBSWATH_PRIORITY['IW3'] == 2
    
    def test_iw1_has_highest_priority(self):
        """Test that IW1 has the highest priority (lowest number)."""
        searcher = CopernicusDataSearcher()
        
        priorities = searcher._SUBSWATH_PRIORITY
        iw1_priority = priorities['IW1']
        
        assert iw1_priority < priorities['IW2']
        assert iw1_priority < priorities['IW3']


class TestTemporalStatistics:
    """Tests for temporal statistics computation."""
    
    def test_temporal_stats_with_valid_data(self):
        """Test temporal statistics with valid date data."""
        searcher = CopernicusDataSearcher()
        
        df = pd.DataFrame({
            'ContentDate': [
                {'Start': '2024-08-01T10:00:00Z'},
                {'Start': '2024-08-07T10:00:00Z'},
                {'Start': '2024-08-13T10:00:00Z'},
                {'Start': '2024-08-19T10:00:00Z'},
                {'Start': '2024-08-25T10:00:00Z'},
            ]
        })
        
        stats = searcher.compute_temporal_statistics(df)
        
        assert stats['total_acquisitions'] == 5
        assert 'temporal_gaps' in stats
        assert stats['temporal_gaps']['min_days'] == 6.0
        assert stats['temporal_gaps']['max_days'] == 6.0
        assert stats['temporal_gaps']['mean_days'] == 6.0
    
    def test_temporal_stats_with_varying_gaps(self):
        """Test temporal statistics with varying gap sizes."""
        searcher = CopernicusDataSearcher()
        
        df = pd.DataFrame({
            'ContentDate': [
                {'Start': '2024-08-01T10:00:00Z'},
                {'Start': '2024-08-04T10:00:00Z'},   # 3 days
                {'Start': '2024-08-16T10:00:00Z'},  # 12 days
                {'Start': '2024-08-22T10:00:00Z'},  # 6 days
            ]
        })
        
        stats = searcher.compute_temporal_statistics(df)
        
        assert stats['temporal_gaps']['min_days'] == 3.0
        assert stats['temporal_gaps']['max_days'] == 12.0
        assert abs(stats['temporal_gaps']['mean_days'] - 7.0) < 0.1
    
    def test_temporal_stats_empty_df(self):
        """Test temporal statistics with empty DataFrame."""
        searcher = CopernicusDataSearcher()
        
        df = pd.DataFrame()
        stats = searcher.compute_temporal_statistics(df)
        
        assert stats == {}
    
    def test_temporal_stats_single_acquisition(self):
        """Test temporal statistics with single acquisition."""
        searcher = CopernicusDataSearcher()
        
        df = pd.DataFrame({
            'ContentDate': [{'Start': '2024-08-01T10:00:00Z'}]
        })
        
        stats = searcher.compute_temporal_statistics(df)
        
        assert stats['total_acquisitions'] == 1
        assert stats['temporal_gaps'] is None
    
    def test_temporal_stats_uses_stored_df(self):
        """Test that temporal statistics uses stored DataFrame when not provided."""
        searcher = CopernicusDataSearcher()
        searcher.df = pd.DataFrame({
            'ContentDate': [
                {'Start': '2024-08-01T10:00:00Z'},
                {'Start': '2024-08-07T10:00:00Z'},
            ]
        })
        
        stats = searcher.compute_temporal_statistics()
        
        assert stats['total_acquisitions'] == 2


class TestCoverageCalculation:
    """Tests for AOI coverage percentage calculation."""
    
    def test_calculate_coverage_requires_shapely(self):
        """Test that coverage calculation gracefully handles missing shapely."""
        searcher = CopernicusDataSearcher()
        searcher.aoi_wkt = 'POLYGON((10.0 45.0, 12.0 45.0, 12.0 47.0, 10.0 47.0, 10.0 45.0))'
        
        # Method should not raise even if shapely is missing
        # It should return None or a value
        result = searcher._calculate_aoi_coverage(
            'POLYGON((10.0 45.0, 12.0 45.0, 12.0 47.0, 10.0 47.0, 10.0 45.0))'
        )
        
        # Result should be a number or None
        assert result is None or isinstance(result, (int, float))


class TestPlotTemporalDistribution:
    """Tests for temporal distribution plotting."""
    
    def test_plot_requires_matplotlib(self):
        """Test that plotting raises ImportError when matplotlib is missing."""
        searcher = CopernicusDataSearcher()
        df = pd.DataFrame({
            'ContentDate': [
                {'Start': '2024-08-01T10:00:00Z'},
                {'Start': '2024-08-07T10:00:00Z'},
            ]
        })
        
        # This should either work (if matplotlib installed) or raise ImportError
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                output_path = os.path.join(tmpdir, 'test_plot.png')
                result = searcher.plot_temporal_distribution(df, output_path=output_path, show=False)
                # If matplotlib is available, check the file was created
                if result:
                    assert os.path.exists(result)
        except ImportError:
            # This is expected if matplotlib is not installed
            pass


class TestDownloadProducts:
    """Tests for product download functionality."""
    
    @patch('phidown.search.pull_down')
    def test_download_products_success(self, mock_pull_down):
        """Test successful product download."""
        mock_pull_down.return_value = None
        
        searcher = CopernicusDataSearcher()
        df = pd.DataFrame({
            'Name': ['product1.SAFE', 'product2.SAFE'],
            'S3Path': ['s3://bucket/path1', 's3://bucket/path2'],
            'ContentLength': [1000, 2000]
        })
        
        with tempfile.TemporaryDirectory() as tmpdir:
            result = searcher.download_products(
                df=df,
                output_dir=tmpdir,
                validate=False,
                verbose=False,
                show_progress=False
            )
            
            assert result['downloaded'] == 2
            assert result['failed'] == 0
            assert len(result['details']) == 2
    
    def test_download_products_empty_df(self):
        """Test download with empty DataFrame."""
        searcher = CopernicusDataSearcher()
        
        result = searcher.download_products(
            df=pd.DataFrame(),
            output_dir='.',
            verbose=False
        )
        
        assert result['downloaded'] == 0
        assert result['failed'] == 0
    
    def test_download_products_missing_s3path(self):
        """Test download handles missing S3Path gracefully."""
        searcher = CopernicusDataSearcher()
        df = pd.DataFrame({
            'Name': ['product1.SAFE'],
            'ContentLength': [1000]
            # S3Path intentionally missing
        })
        
        with tempfile.TemporaryDirectory() as tmpdir:
            result = searcher.download_products(
                df=df,
                output_dir=tmpdir,
                verbose=False
            )
            
            assert result['failed'] == 1
            assert result['downloaded'] == 0


class TestDownloadBursts:
    """Tests for burst download functionality."""
    
    def test_download_bursts_requires_credentials(self):
        """Test that burst download requires credentials."""
        searcher = CopernicusDataSearcher()
        df = pd.DataFrame({
            'Id': ['burst-id-1'],
            'BurstId': [123]
        })
        
        with pytest.raises(ValueError, match='username and password are required'):
            searcher.download_bursts(
                df=df,
                output_dir='.',
                username=None,
                password=None
            )
    
    def test_download_bursts_empty_df(self):
        """Test burst download with empty DataFrame."""
        searcher = CopernicusDataSearcher()
        
        result = searcher.download_bursts(
            df=pd.DataFrame(),
            output_dir='.',
            username='user',
            password='pass',
            verbose=False
        )
        
        assert result['downloaded'] == 0
        assert result['failed'] == 0


class TestFindOptimalBursts:
    """Tests for optimal burst finding with subswath preferences."""
    
    def test_find_optimal_bursts_requires_aoi(self):
        """Test that find_optimal_bursts requires AOI."""
        searcher = CopernicusDataSearcher()
        
        with pytest.raises(ValueError, match='AOI WKT is required'):
            searcher.find_optimal_bursts(
                start_date='2024-08-01T00:00:00Z',
                end_date='2024-08-15T00:00:00Z'
            )
    
    def test_find_optimal_bursts_requires_dates(self):
        """Test that find_optimal_bursts requires dates."""
        searcher = CopernicusDataSearcher()
        
        with pytest.raises(ValueError, match='dates are required'):
            searcher.find_optimal_bursts(
                aoi_wkt='POLYGON((10.0 45.0, 12.0 45.0, 12.0 47.0, 10.0 47.0, 10.0 45.0))'
            )


class TestFindOptimalOrbit:
    """Tests for optimal orbit finding."""
    
    def test_find_optimal_orbit_requires_aoi(self):
        """Test that find_optimal_orbit requires AOI."""
        searcher = CopernicusDataSearcher()
        
        with pytest.raises(ValueError, match='AOI WKT is required'):
            searcher.find_optimal_orbit(
                start_date='2024-08-01T00:00:00Z',
                end_date='2024-08-15T00:00:00Z'
            )
    
    def test_find_optimal_orbit_requires_dates(self):
        """Test that find_optimal_orbit requires dates."""
        searcher = CopernicusDataSearcher()
        
        with pytest.raises(ValueError, match='dates are required'):
            searcher.find_optimal_orbit(
                aoi_wkt='POLYGON((10.0 45.0, 12.0 45.0, 12.0 47.0, 10.0 47.0, 10.0 45.0))'
            )


class TestIntegration:
    """Integration tests requiring network access."""
    
    @pytest.mark.skip(reason='Requires network access')
    def test_search_with_coverage_column(self):
        """Test that search results include coverage column."""
        searcher = CopernicusDataSearcher()
        
        searcher.query_by_filter(
            collection_name='SENTINEL-1',
            product_type='SLC',
            aoi_wkt='POLYGON((10.5 44.5, 12.5 44.5, 12.5 46.0, 10.5 46.0, 10.5 44.5))',
            start_date='2024-08-01T00:00:00Z',
            end_date='2024-08-05T00:00:00Z',
            top=5
        )
        
        df = searcher.execute_query()
        
        assert 'coverage' in df.columns
    
    @pytest.mark.skip(reason='Requires network access')
    def test_find_optimal_orbit_integration(self):
        """Test optimal orbit finding with real API."""
        searcher = CopernicusDataSearcher()
        
        result = searcher.find_optimal_orbit(
            aoi_wkt='POLYGON((10.5 44.5, 12.5 44.5, 12.5 46.0, 10.5 46.0, 10.5 44.5))',
            start_date='2024-08-01T00:00:00Z',
            end_date='2024-08-31T00:00:00Z'
        )
        
        assert 'ascending' in result
        assert 'descending' in result
        assert 'recommended' in result


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
