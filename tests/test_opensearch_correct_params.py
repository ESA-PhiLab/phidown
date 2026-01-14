"""
Test Sentinel-1 parameters using CORRECT names from OpenSearch API

Based on the actual OpenSearch description XML, the correct parameter names are:
- platform (not platformSerialIdentifier)
- instrument (not instrumentShortName)
- sensorMode (not operationalMode)
- polarisation (not polarisationChannels)
"""
from phidown.search import CopernicusDataSearcher
import time


def test_param(param_name, param_value, start_date='2015-06-01', end_date='2015-06-30'):
    """Test a parameter with the actual API."""
    try:
        searcher = CopernicusDataSearcher()
        searcher.query_by_filter(
            collection_name='SENTINEL-1',
            product_type='GRD',
            start_date=start_date,
            end_date=end_date,
            attributes={param_name: param_value},
            top=5
        )
        df = searcher.execute_query()
        return len(df), None
    except Exception as e:
        return 0, str(e)


print("="*80)
print("TESTING CORRECT SENTINEL-1 PARAMETERS FROM OPENSEARCH API")
print("="*80)

tests = [
    # Platform (correct name from OpenSearch)
    ('platform', 'S1A', '2015-06-01', '2015-06-30'),
    ('platform', 'S1B', '2017-06-01', '2017-06-30'),
    
    # Instrument (correct name from OpenSearch)
    ('instrument', 'SAR', '2015-06-01', '2015-06-30'),
    
    # SensorMode (correct name from OpenSearch)
    ('sensorMode', 'IW', '2015-06-01', '2015-06-30'),
    ('sensorMode', 'EW', '2015-06-01', '2015-06-30'),
    ('sensorMode', 'SM', '2015-06-01', '2015-06-30'),
    ('sensorMode', 'WV', '2015-06-01', '2015-06-30'),
    
    # Polarisation (correct name from OpenSearch)
    ('polarisation', 'HH', '2015-06-01', '2015-06-30'),
    ('polarisation', 'VV', '2015-06-01', '2015-06-30'),
    ('polarisation', 'HH&VH', '2015-06-01', '2015-06-30'),
    ('polarisation', 'VV&VH', '2015-06-01', '2015-06-30'),
    
    # Processing Level (correct values from OpenSearch)
    ('processingLevel', 'LEVEL0', '2015-06-01', '2015-06-30'),
    ('processingLevel', 'LEVEL1', '2015-06-01', '2015-06-30'),
    ('processingLevel', 'LEVEL2', '2015-06-01', '2015-06-30'),
    
    # Timeliness (correct values from OpenSearch)
    ('timeliness', 'NRT-10m', '2022-01-01', '2022-01-31'),
    ('timeliness', 'NRT-3h', '2022-01-01', '2022-01-31'),
    ('timeliness', 'Fast-24h', '2022-01-01', '2022-01-31'),
    ('timeliness', 'Off-line', '2022-01-01', '2022-01-31'),
    
    # Orbit Direction
    ('orbitDirection', 'ASCENDING', '2015-06-01', '2015-06-30'),
    ('orbitDirection', 'DESCENDING', '2015-06-01', '2015-06-30'),
    
    # Status
    ('status', 'ONLINE', '2015-06-01', '2015-06-30'),
    ('status', 'OFFLINE', '2015-06-01', '2015-06-30'),
    ('status', 'ALL', '2015-06-01', '2015-06-30'),
    
    # Swath
    ('swath', 'IW', '2015-06-01', '2015-06-30'),
    ('swath', 'IW1', '2015-06-01', '2015-06-30'),
    ('swath', 'IW2', '2015-06-01', '2015-06-30'),
]

print("\nTesting all parameters:\n")
working = []
not_working = []

for param_name, param_value, start, end in tests:
    count, error = test_param(param_name, param_value, start, end)
    status = '✓' if count > 0 else ('✗' if error else '⚠')
    
    result_str = f"{status} {param_name}='{param_value}': {count} results"
    if error:
        result_str += f" (ERROR: {error[:60]})"
    
    print(result_str)
    
    if count > 0:
        working.append((param_name, param_value, count))
    else:
        not_working.append((param_name, param_value, error))
    
    time.sleep(0.1)

print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print(f"\n✓ Working parameters: {len(working)}/{len(tests)}")
print(f"⚠/✗ Not working: {len(not_working)}/{len(tests)}")

if working:
    print("\n✓ WORKING PARAMETERS:")
    for param, value, count in working:
        print(f"  - {param}='{value}' ({count} results)")

if not_working:
    print("\n⚠/✗ NOT WORKING:")
    for param, value, error in not_working:
        if error:
            print(f"  - {param}='{value}': {error[:80]}")
        else:
            print(f"  - {param}='{value}': No results (may need different date range)")
