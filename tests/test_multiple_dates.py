#!/usr/bin/env python3
"""Test script for AIS data download with multiple dates."""

from phidown.ais import download_ais_data
from datetime import datetime, timedelta

def test_multiple_dates():
    """Test AIS data download with several dates to find available data."""
    print("Testing AIS data download with multiple dates...")
    print("=" * 60)
    
    # Try several dates, going backwards from a reasonable date
    base_date = datetime(2024, 8, 25)  # Try August 2024
    
    for i in range(10):  # Try 10 different dates
        test_date = base_date - timedelta(days=i)
        date_str = test_date.strftime("%Y-%m-%d")
        
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