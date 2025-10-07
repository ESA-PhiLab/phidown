"""
Example script demonstrating Sentinel-1 SLC Burst mode usage.

This example shows how to search for Sentinel-1 SLC Bursts using the phidown library.
Burst mode is available for Sentinel-1 SLC products from August 2, 2024 onwards.
"""

import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from phidown.search import CopernicusDataSearcher


def example_1_basic_burst_search():
    """Example 1: Basic burst search with temporal filter."""
    print('\n' + '='*80)
    print('Example 1: Basic Burst Search with Temporal Filter')
    print('='*80)
    
    searcher = CopernicusDataSearcher()
    searcher.query_by_filter(
        burst_mode=True,
        start_date='2024-08-01T00:00:00.000Z',
        end_date='2024-08-03T00:00:00.000Z',
        top=5
    )
    
    print(f'Query URL: {searcher._build_query()}')
    print(f'\nFilter condition:\n{searcher.filter_condition}')


def example_2_burst_search_with_spatial_filter():
    """Example 2: Burst search with spatial (AOI) filter."""
    print('\n' + '='*80)
    print('Example 2: Burst Search with Spatial Filter (AOI)')
    print('='*80)
    
    # Define an area of interest (e.g., over Italy)
    aoi = 'POLYGON((12.655118166047592 47.44667197521409, 21.39065656328509 48.347694733853245, 28.334291357162826 41.877123516783655, 17.47086198383573 40.35854475076158, 12.655118166047592 47.44667197521409))'
    
    searcher = CopernicusDataSearcher()
    searcher.query_by_filter(
        burst_mode=True,
        aoi_wkt=aoi,
        start_date='2024-08-01T00:00:00.000Z',
        end_date='2024-08-03T00:00:00.000Z',
        top=5
    )
    
    print(f'Query URL: {searcher._build_query()}')
    print(f'\nFilter condition:\n{searcher.filter_condition}')


def example_3_burst_search_by_burst_id():
    """Example 3: Search for a specific burst by Burst ID."""
    print('\n' + '='*80)
    print('Example 3: Search by Burst ID')
    print('='*80)
    
    searcher = CopernicusDataSearcher()
    searcher.query_by_filter(
        burst_mode=True,
        burst_id=15804,
        start_date='2024-08-01T00:00:00.000Z',
        end_date='2024-08-15T00:00:00.000Z',
        top=10
    )
    
    print(f'Query URL: {searcher._build_query()}')
    print(f'\nFilter condition:\n{searcher.filter_condition}')


def example_4_burst_search_by_swath_and_polarisation():
    """Example 4: Search bursts by swath identifier and polarisation."""
    print('\n' + '='*80)
    print('Example 4: Search by Swath Identifier and Polarisation')
    print('='*80)
    
    searcher = CopernicusDataSearcher()
    searcher.query_by_filter(
        burst_mode=True,
        swath_identifier='IW2',
        polarisation_channels='VV',
        start_date='2024-08-01T00:00:00.000Z',
        end_date='2024-08-03T00:00:00.000Z',
        top=5
    )
    
    print(f'Query URL: {searcher._build_query()}')
    print(f'\nFilter condition:\n{searcher.filter_condition}')


def example_5_burst_search_by_parent_product():
    """Example 5: Search bursts from a specific parent product."""
    print('\n' + '='*80)
    print('Example 5: Search by Parent Product Name')
    print('='*80)
    
    parent_product = 'S1A_IW_SLC__1SDV_20240802T060719_20240802T060746_055030_06B44E_E7CC.SAFE'
    
    searcher = CopernicusDataSearcher()
    searcher.query_by_filter(
        burst_mode=True,
        parent_product_name=parent_product,
        start_date='2024-08-01T00:00:00.000Z',
        end_date='2024-08-15T00:00:00.000Z'
    )
    
    print(f'Query URL: {searcher._build_query()}')
    print(f'\nFilter condition:\n{searcher.filter_condition}')


def example_6_advanced_burst_search():
    """Example 6: Advanced burst search with multiple filters."""
    print('\n' + '='*80)
    print('Example 6: Advanced Burst Search with Multiple Filters')
    print('='*80)
    
    searcher = CopernicusDataSearcher()
    searcher.query_by_filter(
        burst_mode=True,
        burst_id=15804,
        swath_identifier='IW2',
        parent_product_type='IW_SLC__1S',
        polarisation_channels='VV',
        orbit_direction='DESCENDING',
        operational_mode='IW',
        platform_serial_identifier='A',
        relative_orbit_number=8,
        start_date='2024-08-01T00:00:00.000Z',
        end_date='2024-08-15T00:00:00.000Z',
        order_by='ContentDate/Start desc',
        count=True,
        top=10
    )
    
    print(f'Query URL: {searcher._build_query()}')
    print(f'\nFilter condition:\n{searcher.filter_condition}')


def example_7_execute_burst_query():
    """Example 7: Execute a burst query and display results."""
    print('\n' + '='*80)
    print('Example 7: Execute Burst Query and Display Results')
    print('='*80)
    
    searcher = CopernicusDataSearcher()
    searcher.query_by_filter(
        burst_mode=True,
        swath_identifier='IW2',
        polarisation_channels='VV',
        orbit_direction='DESCENDING',
        start_date='2024-08-01T00:00:00.000Z',
        end_date='2024-08-03T00:00:00.000Z',
        top=5,
        count=True
    )
    
    try:
        # Execute the query
        df = searcher.execute_query()
        
        print(f'\nQuery URL: {searcher.url}')
        print(f'\nNumber of results: {len(df)}')
        
        if searcher.count and hasattr(searcher, 'num_results'):
            print(f'Total results (with count): {searcher.num_results}')
        
        if not df.empty:
            print(f'\nFirst few results:')
            # Display relevant columns for bursts
            burst_columns = ['Id', 'BurstId', 'SwathIdentifier', 'PolarisationChannels', 
                           'OrbitDirection', 'ContentDate', 'ParentProductName']
            available_columns = [col for col in burst_columns if col in df.columns]
            print(df[available_columns].head())
        else:
            print('\nNo results found.')
            
    except Exception as e:
        print(f'\nNote: To execute queries, you need an active internet connection.')
        print(f'Error: {e}')


def main():
    """Run all examples."""
    print('\n' + '='*80)
    print('SENTINEL-1 SLC BURST MODE EXAMPLES')
    print('='*80)
    print('\nThese examples demonstrate how to use the burst mode feature in phidown.')
    print('Burst mode allows searching for Sentinel-1 SLC burst products.')
    print('Data is available from August 2, 2024 onwards.')
    
    # Run all examples
    example_1_basic_burst_search()
    example_2_burst_search_with_spatial_filter()
    example_3_burst_search_by_burst_id()
    example_4_burst_search_by_swath_and_polarisation()
    example_5_burst_search_by_parent_product()
    example_6_advanced_burst_search()
    example_7_execute_burst_query()
    
    print('\n' + '='*80)
    print('END OF EXAMPLES')
    print('='*80 + '\n')


if __name__ == '__main__':
    main()
