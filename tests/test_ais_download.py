#!/usr/bin/env python3
"""Test script for AIS data download functionality."""

from phidown.ais import download_ais_data

def test_ais_download():
    """Test basic AIS data download with debugging output."""
    print("Testing AIS data download...")
    print("=" * 50)
    
    try:
        # Try downloading data for a known available past date
        df = download_ais_data('2023-01-15')  # Use a reliable past date
        
        print(f"\n✅ Download completed successfully!")
        print(f"Result shape: {df.shape}")
        print(f"Columns: {df.columns.tolist()}")
        
        if not df.empty:
            print(f"\nFirst 5 rows:")
            print(df.head())
            print(f"\nData types:")
            print(df.dtypes)
        else:
            print("\n⚠️  DataFrame is empty - no data for this date")
            
    except Exception as e:
        print(f"\n❌ Error occurred: {e}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_ais_download()