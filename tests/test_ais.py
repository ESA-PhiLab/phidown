"""Tests for AIS data handling functionality."""

import pytest
from datetime import date, time
from unittest.mock import Mock, patch
import pandas as pd

from phidown.ais import AISDataHandler, download_ais_data


class TestAISDataHandler:
    """Test cases for AISDataHandler class."""
    
    def test_init(self):
        """Test AISDataHandler initialization."""
        handler = AISDataHandler()
        assert handler.hf_repo_id == "Lore0123/AISPortal"
        assert handler.file_template == "{date}_ais.parquet"
        assert handler.date_format == "%Y-%m-%d"
        assert handler._errors == []
    
    def test_init_custom_params(self):
        """Test AISDataHandler initialization with custom parameters."""
        handler = AISDataHandler(
            hf_repo_id="custom/repo",
            file_template="ais_{date}.parquet",
            date_format="%d-%m-%Y"
        )
        assert handler.hf_repo_id == "custom/repo"
        assert handler.file_template == "ais_{date}.parquet"
        assert handler.date_format == "%d-%m-%Y"
    
    def test_parse_date_string(self):
        """Test date parsing from string."""
        handler = AISDataHandler()
        
        # Valid date string
        result = handler._parse_date("2025-08-25")
        assert result == date(2025, 8, 25)
        
        # Invalid date string
        result = handler._parse_date("invalid-date")
        assert result is None
        
        # Empty string
        result = handler._parse_date("")
        assert result is None
        
        # None
        result = handler._parse_date(None)
        assert result is None
    
    def test_parse_date_object(self):
        """Test date parsing from date object."""
        handler = AISDataHandler()
        test_date = date(2025, 8, 25)
        
        result = handler._parse_date(test_date)
        assert result == test_date
    
    def test_parse_time_string(self):
        """Test time parsing from string."""
        handler = AISDataHandler()
        
        # Valid time with seconds
        result = handler._parse_time("14:30:45")
        assert result == time(14, 30, 45)
        
        # Valid time without seconds
        result = handler._parse_time("14:30")
        assert result == time(14, 30, 0)
        
        # Invalid time string
        result = handler._parse_time("invalid-time")
        assert result is None
        
        # Empty string
        result = handler._parse_time("")
        assert result is None
        
        # None
        result = handler._parse_time(None)
        assert result is None
    
    def test_parse_time_object(self):
        """Test time parsing from time object."""
        handler = AISDataHandler()
        test_time = time(14, 30, 45)
        
        result = handler._parse_time(test_time)
        assert result == test_time
    
    def test_iterate_dates(self):
        """Test date range iteration."""
        handler = AISDataHandler()
        
        # Single day
        start = date(2025, 8, 25)
        end = date(2025, 8, 25)
        result = handler._iterate_dates(start, end)
        assert result == [date(2025, 8, 25)]
        
        # Multiple days
        start = date(2025, 8, 25)
        end = date(2025, 8, 27)
        result = handler._iterate_dates(start, end)
        expected = [date(2025, 8, 25), date(2025, 8, 26), date(2025, 8, 27)]
        assert result == expected
        
        # Reversed dates (should be swapped)
        start = date(2025, 8, 27)
        end = date(2025, 8, 25)
        result = handler._iterate_dates(start, end)
        expected = [date(2025, 8, 25), date(2025, 8, 26), date(2025, 8, 27)]
        assert result == expected
    
    def test_normalize_column_key(self):
        """Test column name normalization."""
        handler = AISDataHandler()
        
        assert handler._normalize_column_key("Latitude") == "latitude"
        assert handler._normalize_column_key("Ship_Name") == "shipname"
        assert handler._normalize_column_key("MMSI-ID") == "mmsiid"
        assert handler._normalize_column_key("123ABC") == "123abc"
    
    def test_find_column(self):
        """Test flexible column finding."""
        handler = AISDataHandler()
        
        # Create test DataFrame
        df = pd.DataFrame(columns=["Ship_Name", "Latitude", "Longitude", "MMSI_ID"])
        
        # Test successful matches
        assert handler._find_column(df, ["name", "shipname"]) == "Ship_Name"
        assert handler._find_column(df, ["lat", "latitude"]) == "Latitude"
        assert handler._find_column(df, ["lon", "longitude"]) == "Longitude"
        assert handler._find_column(df, ["mmsi", "mmsi_id"]) == "MMSI_ID"
        
        # Test no match
        assert handler._find_column(df, ["nonexistent"]) is None
    
    def test_build_time_mask_no_filtering(self):
        """Test time mask with no time filtering."""
        handler = AISDataHandler()
        
        # Create test series
        timestamps = pd.Series(["2025-08-25 10:00:00", "2025-08-25 12:00:00"])
        
        # No time filtering
        result = handler._build_time_mask(timestamps, None, None)
        assert result is None
    
    def test_build_time_mask_with_filtering(self):
        """Test time mask with time filtering."""
        handler = AISDataHandler()
        
        # Create test series
        timestamps = pd.Series([
            "2025-08-25 09:00:00",
            "2025-08-25 11:00:00", 
            "2025-08-25 13:00:00",
            "2025-08-25 15:00:00"
        ])
        
        # Filter between 10:00 and 14:00
        start_time = time(10, 0, 0)
        end_time = time(14, 0, 0)
        
        mask = handler._build_time_mask(timestamps, start_time, end_time)
        expected = pd.Series([False, True, True, False])
        
        pd.testing.assert_series_equal(mask, expected)
    
    @patch('phidown.ais.hf_hub_download')
    def test_load_ais_points_success(self, mock_download):
        """Test successful AIS data loading."""
        handler = AISDataHandler()
        
        # Mock downloaded file path
        mock_download.return_value = "/tmp/test_file.parquet"
        
        # Create mock DataFrame
        mock_data = pd.DataFrame({
            'lat': [51.5, 52.0],
            'lon': [4.0, 4.5],
            'name': ['Ship A', 'Ship B'],
            'mmsi': ['123456789', '987654321'],
            'timestamp': ['2025-08-25 10:00:00', '2025-08-25 11:00:00']
        })
        
        with patch('pandas.read_parquet', return_value=mock_data):
            dates = [date(2025, 8, 25)]
            result = handler._load_ais_points(dates, None, None)
            
            assert len(result) == 2
            assert list(result.columns) == ['name', 'lat', 'lon', 'source_date', 'timestamp', 'mmsi']
            assert result['source_date'].iloc[0] == '2025-08-25'
    
    def test_get_ais_data_invalid_date(self):
        """Test error handling for invalid dates."""
        handler = AISDataHandler()
        
        with pytest.raises(ValueError, match="Invalid start_date"):
            handler.get_ais_data("invalid-date")
    
    def test_filter_by_aoi_no_shapely(self):
        """Test AOI filtering when shapely is not available."""
        handler = AISDataHandler()
        
        # Create test DataFrame
        df = pd.DataFrame({
            'lat': [51.5, 52.0],
            'lon': [4.0, 4.5],
            'name': ['Ship A', 'Ship B']
        })
        
        # Mock shapely as unavailable
        with patch('phidown.ais.SHAPELY_AVAILABLE', False):
            with pytest.raises(ValueError, match="AOI filtering unavailable"):
                handler._filter_by_aoi(df, "POLYGON((4.0 51.0,5.0 51.0,5.0 52.0,4.0 52.0,4.0 51.0))")


def test_download_ais_data_convenience_function():
    """Test the convenience function."""
    with patch('phidown.ais.AISDataHandler') as mock_handler_class:
        mock_handler = Mock()
        mock_handler.get_ais_data.return_value = pd.DataFrame()
        mock_handler_class.return_value = mock_handler
        
        result = download_ais_data("2025-08-25")
        
        mock_handler_class.assert_called_once_with(hf_repo_id="Lore0123/AISPortal")
        mock_handler.get_ais_data.assert_called_once_with("2025-08-25", None, None, None, None)
        assert isinstance(result, pd.DataFrame)