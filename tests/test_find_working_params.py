"""
Find ACTUAL working parameter names for OData API

The OpenSearch API uses different names than the OData API.
This script tests BOTH naming conventions to find what actually works.
"""
from phidown.search import CopernicusDataSearcher


def test_param(param_name, param_value):
    """Test a parameter."""
    try:
        searcher = CopernicusDataSearcher()
        searcher.query_by_filter(
            collection_name='SENTINEL-1',
            product_type='GRD',
            start_date='2015-06-01',
            end_date='2015-06-30',
            attributes={param_name: param_value},
            top=3
        )
        df = searcher.execute_query()
        if len(df) > 0:
            # Check which attributes are actually in the results
            attrs = df.columns.tolist()
            return len(df), attrs
        return 0, []
    except Exception as e:
        return -1, str(e)[:100]


print("="*80)
print("FINDING ACTUAL WORKING PARAMETERS FOR ODATA API")
print("="*80)

# Test both naming conventions
param_tests = {
    'Platform': [
        ('platform', 'S1A'),
        ('platformSerialIdentifier', 'A'),
        ('platformShortName', 'SENTINEL-1'),
    ],
    'Instrument': [
        ('instrument', 'SAR'),
        ('instrumentShortName', 'SAR'),
    ],
    'Sensor/Operational Mode': [
        ('sensorMode', 'IW'),
        ('operationalMode', 'IW'),
    ],
    'Swath': [
        ('swath', 'IW'),
        ('swathIdentifier', 'IW'),
    ],
    'Polarisation': [
        ('polarisation', 'VV'),
        ('polarisationChannels', 'VV'),
    ],
}

print("\nTesting parameter name variations:\n")

for category, tests in param_tests.items():
    print(f"\n{category}:")
    for param_name, param_value in tests:
        count, result = test_param(param_name, param_value)
        if count > 0:
            print(f"  ✓ {param_name}='{param_value}': {count} results")
        elif count == 0:
            print(f"  ⚠ {param_name}='{param_value}': 0 results")
        else:
            print(f"  ✗ {param_name}='{param_value}': ERROR - {result}")

# Now test one working query and see ALL available attributes
print("\n" + "="*80)
print("CHECKING AVAILABLE ATTRIBUTES IN RESULTS")
print("="*80)

searcher = CopernicusDataSearcher()
searcher.query_by_filter(
    collection_name='SENTINEL-1',
    product_type='GRD',
    start_date='2015-06-01',
    end_date='2015-06-07',
    top=1
)
df = searcher.execute_query()

if len(df) > 0:
    print(f"\nFound {len(df)} product(s)")
    print("\nAll available attributes/columns:")
    for col in sorted(df.columns):
        value = df[col].iloc[0]
        if isinstance(value, str) and len(value) > 50:
            value = value[:50] + "..."
        print(f"  - {col}: {value}")
