"""Tests for CLI module."""

import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
from phidown.cli import (
    download_by_name,
    download_by_s3path,
    list_products,
    burst_coverage_analysis,
    main,
)


class TestDownloadByName:
    """Test cases for download_by_name function."""
    
    @patch('phidown.cli.pull_down')
    @patch('phidown.cli.CopernicusDataSearcher')
    def test_successful_download(self, mock_searcher_class, mock_pull_down):
        """Test successful product download by name."""
        # Setup mock searcher
        mock_searcher = MagicMock()
        mock_searcher_class.return_value = mock_searcher
        
        # Create mock DataFrame
        mock_df = pd.DataFrame({
            'S3Path': ['/eodata/Sentinel-1/SAR/test.SAFE'],
            'ContentLength': [1024000]
        })
        mock_searcher.query_by_name.return_value = mock_df
        
        # Setup mock pull_down
        mock_pull_down.return_value = True
        
        # Execute
        result = download_by_name(
            product_name='TEST_PRODUCT',
            output_dir='/tmp/test',
            show_progress=False
        )
        
        # Verify
        assert result is True
        mock_searcher.query_by_name.assert_called_once_with('TEST_PRODUCT')
        mock_pull_down.assert_called_once()
    
    @patch('phidown.cli.CopernicusDataSearcher')
    def test_product_not_found(self, mock_searcher_class):
        """Test behavior when product is not found."""
        # Setup mock searcher with empty DataFrame
        mock_searcher = MagicMock()
        mock_searcher_class.return_value = mock_searcher
        mock_searcher.query_by_name.return_value = pd.DataFrame()
        
        # Execute
        result = download_by_name(
            product_name='NONEXISTENT_PRODUCT',
            output_dir='/tmp/test'
        )
        
        # Verify
        assert result is False
    
    @patch('phidown.cli.CopernicusDataSearcher')
    def test_exception_handling(self, mock_searcher_class):
        """Test exception handling during download."""
        # Setup mock to raise exception
        mock_searcher = MagicMock()
        mock_searcher_class.return_value = mock_searcher
        mock_searcher.query_by_name.side_effect = Exception('Network error')
        
        # Execute
        result = download_by_name(
            product_name='TEST_PRODUCT',
            output_dir='/tmp/test'
        )
        
        # Verify
        assert result is False


class TestDownloadByS3Path:
    """Test cases for download_by_s3path function."""
    
    @patch('phidown.cli.pull_down')
    def test_successful_download(self, mock_pull_down):
        """Test successful download by S3 path."""
        mock_pull_down.return_value = True
        
        result = download_by_s3path(
            s3_path='/eodata/Sentinel-1/SAR/test.SAFE',
            output_dir='/tmp/test',
            show_progress=False
        )
        
        assert result is True
        mock_pull_down.assert_called_once()
    
    def test_invalid_s3_path(self):
        """Test validation of S3 path format."""
        result = download_by_s3path(
            s3_path='/invalid/path',
            output_dir='/tmp/test'
        )
        
        assert result is False
    
    @patch('phidown.cli.pull_down')
    def test_download_all_parameter(self, mock_pull_down):
        """Test download_all parameter is passed correctly."""
        mock_pull_down.return_value = True
        
        download_by_s3path(
            s3_path='/eodata/Sentinel-1/SAR/test.SAFE',
            output_dir='/tmp/test',
            download_all=False
        )
        
        # Check that download_all was passed to pull_down
        call_kwargs = mock_pull_down.call_args[1]
        assert call_kwargs['download_all'] is False


class TestMainCLI:
    """Test cases for main CLI entry point."""
    
    @patch('phidown.cli.download_by_name')
    @patch('sys.argv', ['phidown', '--name', 'TEST_PRODUCT', '-o', '/tmp/test'])
    def test_cli_with_name(self, mock_download):
        """Test CLI with --name argument."""
        mock_download.return_value = True
        
        with pytest.raises(SystemExit) as exc_info:
            main()
        
        assert exc_info.value.code == 0
        mock_download.assert_called_once()

    @patch('phidown.cli.download_by_name')
    @patch('sys.argv', ['phidown', '--name', 'TEST_PRODUCT', '-o', '/tmp/test', '--robust'])
    def test_cli_with_name_robust_defaults(self, mock_download):
        """Test robust preset is forwarded to download helper."""
        mock_download.return_value = True

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 0
        kwargs = mock_download.call_args.kwargs
        assert kwargs['retry_count'] == 5
        assert kwargs['read_timeout'] == 900.0
        assert kwargs['resume_mode'] == 'product'
    
    @patch('phidown.cli.download_by_s3path')
    @patch('sys.argv', ['phidown', '--s3path', '/eodata/test', '-o', '/tmp/test'])
    def test_cli_with_s3path(self, mock_download):
        """Test CLI with --s3path argument."""
        mock_download.return_value = True
        
        with pytest.raises(SystemExit) as exc_info:
            main()
        
        assert exc_info.value.code == 0
        mock_download.assert_called_once()
    
    @patch('sys.argv', ['phidown'])
    def test_cli_missing_required_args(self):
        """Test CLI fails when required arguments are missing."""
        with pytest.raises(SystemExit) as exc_info:
            main()
        
        assert exc_info.value.code != 0
    
    @patch('phidown.cli.download_by_name')
    @patch('sys.argv', ['phidown', '--name', 'TEST', '-o', '/tmp/test'])
    def test_cli_failed_download(self, mock_download):
        """Test CLI exit code on failed download."""
        mock_download.return_value = False
        
        with pytest.raises(SystemExit) as exc_info:
            main()
        
        assert exc_info.value.code == 1

    @patch('phidown.cli.list_products')
    @patch(
        'sys.argv',
        [
            'phidown',
            '--list',
            '--collection', 'SENTINEL-1',
            '--product-type', 'GRD',
            '--bbox', '-5', '40', '5', '45',
            '--start-date', '2024-01-01T00:00:00',
            '--end-date', '2024-01-31T23:59:59',
            '--format', 'json'
        ]
    )
    def test_cli_with_list(self, mock_list_products):
        """Test CLI with --list argument."""
        mock_list_products.return_value = True

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 0
        mock_list_products.assert_called_once()

    @patch('phidown.cli.list_products')
    @patch(
        'sys.argv',
        [
            'phidown',
            'list',
            '--collection', 'SENTINEL-1',
            '--product-type', 'GRD',
            '--bbox', '-5', '40', '5', '45',
            '--start-date', '2024-01-01T00:00:00',
            '--end-date', '2024-01-31T23:59:59',
            '--format', 'json'
        ]
    )
    def test_cli_subcommand_list(self, mock_list_products):
        """Test subcommand-style list invocation."""
        mock_list_products.return_value = True

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 0
        mock_list_products.assert_called_once()

    @patch('sys.argv', ['phidown', '--list', '--collection', 'SENTINEL-1', '--start-date', '2024-01-01T00:00:00'])
    def test_cli_list_requires_spatial_filter(self):
        """Test --list requires an AOI filter."""
        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code != 0

    @patch('sys.argv', ['phidown', 'list', '--collection', 'SENTINEL-1', '--start-date', '2024-01-01T00:00:00'])
    def test_cli_subcommand_list_requires_spatial_filter(self):
        """Test `phidown list` requires an AOI filter."""
        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code != 0

    @patch('phidown.cli.burst_coverage_analysis')
    @patch(
        'sys.argv',
        [
            'phidown',
            '--burst-coverage',
            '--bbox', '-5', '40', '5', '45',
            '--start-date', '2024-08-02T00:00:00',
            '--end-date', '2024-08-15T23:59:59',
            '--polarisation', 'VV',
            '--format', 'json'
        ]
    )
    def test_cli_with_burst_coverage(self, mock_burst_coverage):
        """Test CLI with --burst-coverage argument."""
        mock_burst_coverage.return_value = True

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 0
        mock_burst_coverage.assert_called_once()

    @patch('sys.argv', ['phidown', '--burst-coverage', '--bbox', '-5', '40', '5', '45', '--start-date', '2024-08-02T00:00:00'])
    def test_cli_burst_coverage_requires_end_date(self):
        """Test --burst-coverage requires both start and end dates."""
        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code != 0


class TestListProducts:
    """Test cases for list_products function."""

    @patch('phidown.cli.CopernicusDataSearcher')
    def test_list_products_with_bbox(self, mock_searcher_class):
        """Test listing works and bbox is converted to WKT."""
        mock_searcher = MagicMock()
        mock_searcher_class.return_value = mock_searcher
        mock_searcher.execute_query.return_value = pd.DataFrame(
            {
                'Name': ['P1'],
                'S3Path': ['/eodata/path'],
                'ContentDate': ['2024-01-01T00:00:00Z']
            }
        )

        result = list_products(
            collection='SENTINEL-1',
            product_type='GRD',
            bbox=[-5, 40, 5, 45],
            start_date='2024-01-01T00:00:00',
            end_date='2024-01-31T23:59:59',
            output_format='json'
        )

        assert result is True
        mock_searcher.query_by_filter.assert_called_once()
        kwargs = mock_searcher.query_by_filter.call_args.kwargs
        assert kwargs['aoi_wkt'].startswith('POLYGON((')

    @patch('phidown.cli.CopernicusDataSearcher')
    def test_list_products_save_csv(self, mock_searcher_class, tmp_path):
        """Test listing output can be saved to a file."""
        mock_searcher = MagicMock()
        mock_searcher_class.return_value = mock_searcher
        mock_searcher.execute_query.return_value = pd.DataFrame(
            {
                'Name': ['P1'],
                'S3Path': ['/eodata/path']
            }
        )

        output_file = tmp_path / 'products.csv'
        result = list_products(
            collection='SENTINEL-1',
            aoi_wkt='POLYGON((-5 40, 5 40, 5 45, -5 45, -5 40))',
            start_date='2024-01-01T00:00:00',
            output_format='csv',
            save_path=str(output_file)
        )

        assert result is True
        assert output_file.exists()


class TestBurstCoverageAnalysis:
    """Test cases for burst_coverage_analysis function."""

    @patch('phidown.cli.CopernicusDataSearcher')
    def test_burst_coverage_analysis_json(self, mock_searcher_class):
        """Test burst coverage analysis output in JSON format."""
        mock_searcher = MagicMock()
        mock_searcher_class.return_value = mock_searcher
        mock_searcher.find_optimal_bursts.return_value = pd.DataFrame(
            {
                'Id': ['id1'],
                'BurstId': [15804],
                'SwathIdentifier': ['IW2'],
                'coverage': [78.5],
                'ContentDate': ['2024-08-05T00:00:00Z'],
                'S3Path': ['/eodata/Sentinel-1/SAR/']
            }
        )

        result = burst_coverage_analysis(
            bbox=[-5, 40, 5, 45],
            start_date='2024-08-02T00:00:00',
            end_date='2024-08-15T23:59:59',
            polarisation='VV',
            output_format='json'
        )

        assert result is True
        mock_searcher.find_optimal_bursts.assert_called_once()
        kwargs = mock_searcher.find_optimal_bursts.call_args.kwargs
        assert kwargs['aoi_wkt'].startswith('POLYGON((')

    @patch('phidown.cli.CopernicusDataSearcher')
    def test_burst_coverage_analysis_save_csv(self, mock_searcher_class, tmp_path):
        """Test burst coverage analysis can save CSV output."""
        mock_searcher = MagicMock()
        mock_searcher_class.return_value = mock_searcher
        mock_searcher.find_optimal_bursts.return_value = pd.DataFrame(
            {
                'Id': ['id1'],
                'BurstId': [15804],
                'SwathIdentifier': ['IW2'],
                'coverage': [78.5]
            }
        )

        output_file = tmp_path / 'burst_analysis.csv'
        result = burst_coverage_analysis(
            aoi_wkt='POLYGON((-5 40, 5 40, 5 45, -5 45, -5 40))',
            start_date='2024-08-02T00:00:00',
            end_date='2024-08-15T23:59:59',
            output_format='csv',
            save_path=str(output_file)
        )

        assert result is True
        assert output_file.exists()
