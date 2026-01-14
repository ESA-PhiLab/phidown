"""Debug script to test range query format for orbitNumber and cloudCover."""
from phidown.search import CopernicusDataSearcher

print("\n=== Testing different range query formats ===\n")

# Test 1: cloudCover as range string
print("Test 1: cloudCover='[0,20]'")
try:
    searcher = CopernicusDataSearcher()
    searcher.query_by_filter(
        collection_name='SENTINEL-2',
        product_type='S2MSI1C',
        start_date='2016-01-01',
        end_date='2016-01-31',
        attributes={'cloudCover': '[0,20]'},
        top=3
    )
    df = searcher.search()
    print(f"  ✓ Found {len(df)} products")
except Exception as e:
    print(f"  ✗ ERROR: {e}")

# Test 2: cloudCover as numeric value
print("\nTest 2: cloudCover=20 (single value)")
try:
    searcher = CopernicusDataSearcher()
    searcher.query_by_filter(
        collection_name='SENTINEL-2',
        product_type='S2MSI1C',
        start_date='2016-01-01',
        end_date='2016-01-31',
        attributes={'cloudCover': '20'},
        top=3
    )
    df = searcher.search()
    print(f"  ✓ Found {len(df)} products")
except Exception as e:
    print(f"  ✗ ERROR: {e}")

# Test 3: orbitNumber as range
print("\nTest 3: orbitNumber='[1000,2000]'")
try:
    searcher = CopernicusDataSearcher()
    searcher.query_by_filter(
        collection_name='SENTINEL-2',
        product_type='S2MSI1C',
        start_date='2016-01-01',
        end_date='2016-01-31',
        attributes={'orbitNumber': '[1000,2000]'},
        top=3
    )
    df = searcher.search()
    print(f"  ✓ Found {len(df)} products")
except Exception as e:
    print(f"  ✗ ERROR: {e}")

# Test 4: orbitNumber as single value
print("\nTest 4: orbitNumber='1500'")
try:
    searcher = CopernicusDataSearcher()
    searcher.query_by_filter(
        collection_name='SENTINEL-2',
        product_type='S2MSI1C',
        start_date='2016-01-01',
        end_date='2016-01-31',
        attributes={'orbitNumber': '1500'},
        top=3
    )
    df = searcher.search()
    print(f"  ✓ Found {len(df)} products")
    if len(df) > 0:
        print(f"  Example orbitNumber: {df.iloc[0]['orbitNumber']}")
except Exception as e:
    print(f"  ✗ ERROR: {e}")

# Test 5: Check what cloudCover values actually exist
print("\nTest 5: No cloudCover filter (to see actual values)")
try:
    searcher = CopernicusDataSearcher()
    searcher.query_by_filter(
        collection_name='SENTINEL-2',
        product_type='S2MSI1C',
        start_date='2016-01-01',
        end_date='2016-01-07',
        attributes={},
        top=10
    )
    df = searcher.search()
    print(f"  ✓ Found {len(df)} products")
    if len(df) > 0:
        print(f"  Sample cloudCover values: {df['cloudCover'].head().tolist()}")
        print(f"  CloudCover range: {df['cloudCover'].min()} to {df['cloudCover'].max()}")
except Exception as e:
    print(f"  ✗ ERROR: {e}")
