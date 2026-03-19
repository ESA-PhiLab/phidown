"""
Debug script to investigate failing tests
"""
from phidown.search import CopernicusDataSearcher

# Test 1: Check what Sentinel-3 data is available
print("="*80)
print("Investigating Sentinel-3 availability")
print("="*80)

searcher = CopernicusDataSearcher()
searcher.query_by_filter(
    collection_name='SENTINEL-3',
    start_date='2016-01-01',
    end_date='2016-12-31',
    top=10
)
df = searcher.execute_query()
print(f"Found {len(df)} Sentinel-3 products (any type)")
if len(df) > 0:
    print("\nAvailable columns:")
    print(df.columns.tolist())
    print("\nFirst product details:")
    print(df.iloc[0])
    if 'Attributes' in df.columns:
        print("\nAttributes:")
        print(df.iloc[0]['Attributes'])
print()

# Test 2: Check Sentinel-2 L2A availability (should exist from 2017)
print("="*80)
print("Investigating Sentinel-2 L2A availability")
print("="*80)

searcher = CopernicusDataSearcher()
searcher.query_by_filter(
    collection_name='SENTINEL-2',
    product_type='S2MSI2A',
    start_date='2018-01-01',
    end_date='2018-01-31',
    cloud_cover_threshold=50,
    top=5
)
df = searcher.execute_query()
print(f"Found {len(df)} Sentinel-2 L2A products (2018)")
if len(df) > 0:
    print("✓ L2A products exist from 2018")
print()

# Test 3: Check Sentinel-1 polarisation format
print("="*80)
print("Investigating Sentinel-1 polarisation format")
print("="*80)

searcher = CopernicusDataSearcher()
searcher.query_by_filter(
    collection_name='SENTINEL-1',
    product_type='GRD',
    start_date='2015-06-01',
    end_date='2015-06-05',
    top=5
)
df = searcher.execute_query()
if len(df) > 0:
    print("Sample Sentinel-1 product:")
    if 'Attributes' in df.columns:
        print(df.iloc[0]['Attributes'])
