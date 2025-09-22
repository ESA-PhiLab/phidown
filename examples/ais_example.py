#!/usr/bin/env python3
"""Example script demonstrating usage of the AIS data handler."""

from datetime import date, time
from phidown.ais import AISDataHandler, download_ais_data


def example_basic_usage():
    """Example of basic AIS data download."""
    print("=== Basic AIS Data Download ===")
    
    # Download data for a single day
    df = download_ais_data("2025-08-25")
    print(f"Downloaded {len(df)} AIS records for 2025-08-25")
    print(f"Columns: {list(df.columns)}")
    
    if not df.empty:
        print(f"Sample data:")
        print(df.head(3))


def example_time_filtering():
    """Example of AIS data download with time filtering."""
    print("\n=== AIS Data Download with Time Filtering ===")
    
    # Download with time window (10:00 to 12:00 UTC)
    df = download_ais_data(
        start_date="2025-08-25",
        start_time="10:00:00",
        end_time="12:00:00"
    )
    print(f"Downloaded {len(df)} AIS records for 2025-08-25 between 10:00-12:00 UTC")


def example_aoi_filtering():
    """Example of AIS data download with Area of Interest filtering."""
    print("\n=== AIS Data Download with AOI Filtering ===")
    
    # Define AOI around Netherlands coast
    aoi_wkt = """POLYGON((4.2100 51.3700,4.4800 51.3700,4.5100 51.2900,
                 4.4650 51.1700,4.2500 51.1700,4.1900 51.2500,4.2100 51.3700))"""
    
    try:
        df = download_ais_data(
            start_date="2025-08-25",
            aoi_wkt=aoi_wkt
        )
        print(f"Downloaded {len(df)} AIS records within AOI for 2025-08-25")
        
        if not df.empty:
            print(f"Lat range: {df['lat'].min():.4f} to {df['lat'].max():.4f}")
            print(f"Lon range: {df['lon'].min():.4f} to {df['lon'].max():.4f}")
    except ValueError as e:
        print(f"AOI filtering failed: {e}")


def example_advanced_usage():
    """Example of advanced usage with AISDataHandler class."""
    print("\n=== Advanced Usage with AISDataHandler ===")
    
    # Create handler instance
    handler = AISDataHandler()
    
    # Download data for date range with all filters
    try:
        df = handler.get_ais_data(
            start_date=date(2025, 8, 25),
            end_date=date(2025, 8, 26),
            start_time=time(9, 0, 0),
            end_time=time(15, 0, 0),
            aoi_wkt="POLYGON((4.0 51.0,5.0 51.0,5.0 52.0,4.0 52.0,4.0 51.0))"
        )
        
        print(f"Downloaded {len(df)} AIS records")
        
        # Check for errors
        errors = handler.get_errors()
        if errors:
            print(f"Encountered {len(errors)} errors:")
            for error in errors[:3]:  # Show first 3 errors
                print(f"  - {error}")
        
        # Analyze data
        if not df.empty:
            unique_vessels = df[df['name'] != '']['name'].nunique()
            print(f"Unique vessels with names: {unique_vessels}")
            
            by_date = df.groupby('source_date').size()
            print(f"Records per day:")
            for date_str, count in by_date.items():
                print(f"  {date_str}: {count}")
                
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    # Run examples
    example_basic_usage()
    example_time_filtering()
    example_aoi_filtering()
    example_advanced_usage()