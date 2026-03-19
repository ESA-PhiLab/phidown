"""
Test to understand Sentinel-3 product types
"""
from phidown.search import CopernicusDataSearcher

# Test with S3OLCI as per config.json
print("="*80)
print("Test 1: Using S3OLCI (from config.json)")
print("="*80)
searcher = CopernicusDataSearcher()
searcher.query_by_filter(
    collection_name='SENTINEL-3',
    product_type='S3OLCI',
    start_date='2016-06-01',
    end_date='2016-06-05',
    top=5
)
df = searcher.execute_query()
print(f"Found {len(df)} products")
if len(df) > 0:
    print("\nSample product types found:")
    for pt in df['Name'].head():
        # Extract product type from filename
        parts = pt.split('_')
        if len(parts) >= 3:
            prod_type = '_'.join(parts[:3]) + '___'
            print(f"  {prod_type}")
