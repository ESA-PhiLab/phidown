#!/usr/bin/env python3
"""Test script for AIS data download with multiple dates."""

from phidown.ais import download_ais_data
from datetime import datetime, timedelta
from unittest.mock import patch
import pandas as pd

def test_multiple_dates():
    """
    Test AIS data download with several dates to find available data.

    Returns:
        None
    """
    print('Testing AIS data download with multiple dates...')
    print('=' * 60)

    base_date = datetime(2024, 1, 1)  # Use a fixed date for deterministic tests

    def mock_download_ais_data(date_str, start_time=None, end_time=None):
        """
        Mock download_ais_data to return a DataFrame for a specific date.

        Args:
            date_str (str): Date string.
            start_time (str, optional): Start time.
            end_time (str, optional): End time.

        Returns:
            pd.DataFrame: Mocked DataFrame.
        """
        if date_str == '2024-01-01':
            data = {'col1': [1, 2, 3], 'col2': ['a', 'b', 'c']}
            return pd.DataFrame(data)
        return pd.DataFrame()

    with patch('phidown.ais.download_ais_data', side_effect=mock_download_ais_data):
        for i in range(10):
            test_date = base_date - timedelta(days=i)
            date_str = test_date.strftime('%Y-%m-%d')
        
        print(f"\nTrying date: {date_str}")
        print("-" * 40)
        
        try:
            df = download_ais_data(date_str)
            
            if not df.empty:
                print(f"✅ SUCCESS! Found data for {date_str}")
                print(f"Result shape: {df.shape}")
                print(f"Sample data:")
                print(df.head(3))
                
                # Test time filtering
                print(f"\nTesting time filtering...")
                df_filtered = download_ais_data(
                    date_str, 
                    start_time="10:00:00", 
                    end_time="12:00:00"
                )
                print(f"Filtered (10:00-12:00): {df_filtered.shape[0]} rows")
                
                break
            else:
                print(f"❌ No data available for {date_str}")
                
        except Exception as e:
            print(f"❌ Error for {date_str}: {e}")
    
    else:
        print("\n⚠️  No data found for any of the tested dates")
        print("The repository might be empty or the dates might be out of range")

if __name__ == "__main__":
    test_multiple_dates()