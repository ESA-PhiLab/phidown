"""Tests for CLI module."""

import pytest
from unittest.mock import MagicMock, patch, call
import pandas as pd
from phidown.cli import download_by_name, download_by_s3path, main
import sys


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
