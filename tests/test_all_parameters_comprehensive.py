"""
Comprehensive Parameter Testing for All Collections

Tests ALL parameters listed in config.json for:
- Sentinel-1
- Sentinel-2
- Sentinel-3
- CCM

Goal: Verify which parameters work and document them properly.
"""
from phidown.search import CopernicusDataSearcher
import time


def test_parameter(collection, product_type, param_name, param_value, start_date, end_date, additional_attrs=None):
    """Test a single parameter and return results."""
    try:
        searcher = CopernicusDataSearcher()
        attrs = {param_name: param_value}
        if additional_attrs:
            attrs.update(additional_attrs)
        
        searcher.query_by_filter(
            collection_name=collection,
            product_type=product_type,
            start_date=start_date,
            end_date=end_date,
            attributes=attrs,
            top=5
        )
        df = searcher.execute_query()
        return len(df), None
    except Exception as e:
        return 0, str(e)


print("="*80)
print("COMPREHENSIVE PARAMETER TESTING")
print("="*80)

# Sentinel-1 Parameters from config.json
print("\n" + "="*80)
print("SENTINEL-1 PARAMETERS")
print("="*80)

s1_tests = [
    # Core parameters that should work
    ('productType', 'GRD', '2015-06-01', '2015-06-30'),
    ('productType', 'SLC', '2015-06-01', '2015-06-30'),
    ('productType', 'OCN', '2015-06-01', '2015-06-30'),
    
    # Platform and instrument
    ('platformSerialIdentifier', 'A', '2015-06-01', '2015-06-30'),
    ('platformSerialIdentifier', 'B', '2017-06-01', '2017-06-30'),
    ('instrumentShortName', 'SAR', '2015-06-01', '2015-06-30'),
    
    # Operational modes
    ('operationalMode', 'IW', '2015-06-01', '2015-06-30'),
    ('operationalMode', 'EW', '2015-06-01', '2015-06-30'),
    ('operationalMode', 'SM', '2015-06-01', '2015-06-30'),
    ('operationalMode', 'WV', '2015-06-01', '2015-06-30'),
    
    # Swath identifiers
    ('swathIdentifier', 'IW', '2015-06-01', '2015-06-30'),
    ('swathIdentifier', 'EW', '2015-06-01', '2015-06-30'),
    ('swathIdentifier', 'S1', '2015-06-01', '2015-06-30'),
    ('swathIdentifier', 'WV', '2015-06-01', '2015-06-30'),
    
    # Polarisation channels
    ('polarisationChannels', 'VV', '2015-06-01', '2015-06-30'),
    ('polarisationChannels', 'VH', '2015-06-01', '2015-06-30'),
    ('polarisationChannels', 'HH', '2015-06-01', '2015-06-30'),
    ('polarisationChannels', 'HV', '2015-06-01', '2015-06-30'),
    
    # Processing level
    ('processingLevel', 'LEVEL1', '2015-06-01', '2015-06-30'),
    ('processingLevel', 'L1', '2015-06-01', '2015-06-30'),
    ('processingLevel', '1', '2015-06-01', '2015-06-30'),
    
    # Timeliness
    ('timeliness', 'NRT-3h', '2022-01-01', '2022-01-31'),
    ('timeliness', 'NRT-10m', '2022-01-01', '2022-01-31'),
    ('timeliness', 'Fast-24h', '2022-01-01', '2022-01-31'),
    ('timeliness', 'NRT', '2022-01-01', '2022-01-31'),
    ('timeliness', 'NTC', '2022-01-01', '2022-01-31'),
    
    # Orbit direction
    ('orbitDirection', 'ASCENDING', '2015-06-01', '2015-06-30'),
    ('orbitDirection', 'DESCENDING', '2015-06-01', '2015-06-30'),
]

results_s1 = []
for param_name, param_value, start, end in s1_tests:
    count, error = test_parameter('SENTINEL-1', 'GRD', param_name, param_value, start, end)
    status = '✓' if count > 0 else ('✗' if error else '⚠')
    results_s1.append((param_name, param_value, count, status, error))
    print(f"{status} {param_name}='{param_value}': {count} results" + (f" (ERROR: {error[:50]})" if error else ""))
    time.sleep(0.1)

# Sentinel-2 Parameters
print("\n" + "="*80)
print("SENTINEL-2 PARAMETERS")
print("="*80)

s2_tests = [
    # Product types
    ('productType', 'S2MSI1C', '2016-01-01', '2016-01-31'),
    ('productType', 'S2MSI2A', '2018-01-01', '2018-01-31'),
    
    # Platform and instrument
    ('platformSerialIdentifier', 'A', '2016-01-01', '2016-01-31'),
    ('platformSerialIdentifier', 'B', '2017-07-01', '2017-07-31'),
    ('instrumentShortName', 'MSI', '2016-01-01', '2016-01-31'),
    
    # Processing levels
    ('processingLevel', 'L1C', '2016-01-01', '2016-01-31'),
    ('processingLevel', 'L2A', '2018-01-01', '2018-01-31'),
    ('processingLevel', 'LEVEL1C', '2016-01-01', '2016-01-31'),
    ('processingLevel', 'LEVEL2A', '2018-01-01', '2018-01-31'),
    
    # Tile ID
    ('tileId', '32TQM', '2016-01-01', '2016-12-31'),
    ('tileId', '33TWG', '2016-01-01', '2016-12-31'),
    
    # Quality status
    ('qualityStatus', 'PASSED', '2016-01-01', '2016-01-31'),
    ('qualityStatus', 'FAILED', '2016-01-01', '2016-01-31'),
    
    # Operational mode
    ('operationalMode', 'INS-NOBS', '2016-01-01', '2016-01-31'),
]

results_s2 = []
for param_name, param_value, start, end in s2_tests:
    count, error = test_parameter('SENTINEL-2', 'S2MSI1C', param_name, param_value, start, end)
    status = '✓' if count > 0 else ('✗' if error else '⚠')
    results_s2.append((param_name, param_value, count, status, error))
    print(f"{status} {param_name}='{param_value}': {count} results" + (f" (ERROR: {error[:50]})" if error else ""))
    time.sleep(0.1)

# Sentinel-3 Parameters
print("\n" + "="*80)
print("SENTINEL-3 PARAMETERS")
print("="*80)

s3_tests = [
    # Platform and instrument
    ('platformSerialIdentifier', 'A', '2016-06-01', '2016-06-30'),
    ('platformSerialIdentifier', 'B', '2018-06-01', '2018-06-30'),
    ('instrumentShortName', 'OLCI', '2016-06-01', '2016-06-30'),
    ('instrumentShortName', 'SLSTR', '2016-06-01', '2016-06-30'),
    ('instrumentShortName', 'SRAL', '2016-06-01', '2016-06-30'),
    
    # Processing levels
    ('processingLevel', '1', '2016-06-01', '2016-06-30'),
    ('processingLevel', '2', '2016-06-01', '2016-06-30'),
    ('processingLevel', 'L1', '2016-06-01', '2016-06-30'),
    ('processingLevel', 'L2', '2016-06-01', '2016-06-30'),
    ('processingLevel', 'LEVEL1', '2016-06-01', '2016-06-30'),
    ('processingLevel', 'LEVEL2', '2016-06-01', '2016-06-30'),
    
    # Timeliness
    ('timeliness', 'NR', '2016-06-01', '2016-06-30'),
    ('timeliness', 'NT', '2016-06-01', '2016-06-30'),
    ('timeliness', 'ST', '2016-06-01', '2016-06-30'),
    ('timeliness', 'NRT', '2016-06-01', '2016-06-30'),
    ('timeliness', 'NTC', '2016-06-01', '2016-06-30'),
    
    # Orbit direction
    ('orbitDirection', 'ASCENDING', '2016-06-01', '2016-06-30'),
    ('orbitDirection', 'DESCENDING', '2016-06-01', '2016-06-30'),
    
    # Operational mode
    ('operationalMode', 'EO', '2016-06-01', '2016-06-30'),
]

results_s3 = []
for param_name, param_value, start, end in s3_tests:
    # For S3, we need to specify instrument for product search
    if param_name == 'instrumentShortName':
        count, error = test_parameter('SENTINEL-3', None, param_name, param_value, start, end)
    else:
        count, error = test_parameter('SENTINEL-3', None, param_name, param_value, start, end, 
                                     {'instrumentShortName': 'OLCI'})
    status = '✓' if count > 0 else ('✗' if error else '⚠')
    results_s3.append((param_name, param_value, count, status, error))
    print(f"{status} {param_name}='{param_value}': {count} results" + (f" (ERROR: {error[:50]})" if error else ""))
    time.sleep(0.1)

# Summary
print("\n" + "="*80)
print("SUMMARY")
print("="*80)

def print_summary(results, collection_name):
    working = [r for r in results if r[3] == '✓']
    no_results = [r for r in results if r[3] == '⚠']
    errors = [r for r in results if r[3] == '✗']
    
    print(f"\n{collection_name}:")
    print(f"  ✓ Working: {len(working)}/{len(results)}")
    print(f"  ⚠ No results: {len(no_results)}/{len(results)}")
    print(f"  ✗ Errors: {len(errors)}/{len(results)}")
    
    if working:
        print(f"\n  Working parameters:")
        for param, value, count, _, _ in working:
            print(f"    - {param}='{value}' ({count} results)")
    
    if errors:
        print(f"\n  Error parameters:")
        for param, value, _, _, error in errors:
            print(f"    - {param}='{value}': {error[:80]}")

print_summary(results_s1, "SENTINEL-1")
print_summary(results_s2, "SENTINEL-2")
print_summary(results_s3, "SENTINEL-3")
