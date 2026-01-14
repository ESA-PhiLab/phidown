"""
Comprehensive Categorical Attribute Testing for All Collections

Tests ALL possible categorical values for each attribute from config.json:
- Sentinel-1: All product types, operational modes, swaths, polarizations, etc.
- Sentinel-2: All product types, platforms, processing levels, etc.
- Sentinel-3: All instruments, processing levels, timeliness values, etc.

Goal: Document which specific values work for each parameter.
"""
from phidown.search import CopernicusDataSearcher
import time


def test_attribute(collection, product_type, attr_name, attr_value, start_date, end_date, extra_attrs=None):
    """Test a single attribute value."""
    try:
        searcher = CopernicusDataSearcher()
        attrs = {attr_name: attr_value}
        if extra_attrs:
            attrs.update(extra_attrs)
        
        searcher.query_by_filter(
            collection_name=collection,
            product_type=product_type,
            start_date=start_date,
            end_date=end_date,
            attributes=attrs,
            top=3
        )
        df = searcher.execute_query()
        return len(df), None
    except Exception as e:
        return 0, str(e)[:80]


print("="*90)
print("COMPREHENSIVE CATEGORICAL ATTRIBUTE TESTING")
print("="*90)
print("\nTesting ALL possible categorical values from config.json\n")

# ============================================================================
# SENTINEL-1 COMPREHENSIVE TESTING
# ============================================================================
print("\n" + "="*90)
print("SENTINEL-1 - COMPREHENSIVE CATEGORICAL TESTING")
print("="*90)

s1_categories = {
    'productType': {
        'values': ['GRD', 'SLC', 'OCN', 'RAW'],
        'date': ('2015-06-01', '2015-06-30')
    },
    'platformSerialIdentifier': {
        'values': ['A', 'B', 'C'],
        'date': ('2015-06-01', '2015-06-30')
    },
    'instrumentShortName': {
        'values': ['SAR'],
        'date': ('2015-06-01', '2015-06-30')
    },
    'operationalMode': {
        'values': ['IW', 'EW', 'SM', 'WV'],
        'date': ('2015-06-01', '2015-06-30')
    },
    'swathIdentifier': {
        'values': ['IW', 'EW', 'S1', 'S2', 'S3', 'S4', 'S5', 'S6', 'WV'],
        'date': ('2015-06-01', '2015-06-30')
    },
    'polarisationChannels': {
        'values': ['VV', 'VH', 'HH', 'HV'],
        'date': ('2015-06-01', '2015-06-30')
    },
    'processingLevel': {
        'values': ['RAW', 'LEVEL0', 'LEVEL1', 'LEVEL2', 'L1', '1'],
        'date': ('2015-06-01', '2015-06-30')
    },
    'timeliness': {
        'values': ['NRT-3h', 'NRT-10m', 'Fast-24h', 'Off-line', 'Reprocessing', 'NRT', 'NTC'],
        'date': ('2022-01-01', '2022-01-31')
    },
    'orbitDirection': {
        'values': ['ASCENDING', 'DESCENDING'],
        'date': ('2015-06-01', '2015-06-30')
    }
}

s1_results = {}
for attr_name, config in s1_categories.items():
    print(f"\n{attr_name}:")
    s1_results[attr_name] = {'working': [], 'no_results': [], 'errors': []}
    
    for value in config['values']:
        start, end = config['date']
        count, error = test_attribute('SENTINEL-1', 'GRD', attr_name, value, start, end)
        
        if count > 0:
            print(f"  ✓ {value}: {count} results")
            s1_results[attr_name]['working'].append((value, count))
        elif error:
            print(f"  ✗ {value}: ERROR - {error}")
            s1_results[attr_name]['errors'].append((value, error))
        else:
            print(f"  ⚠ {value}: 0 results")
            s1_results[attr_name]['no_results'].append(value)
        
        time.sleep(0.05)

# ============================================================================
# SENTINEL-2 COMPREHENSIVE TESTING
# ============================================================================
print("\n" + "="*90)
print("SENTINEL-2 - COMPREHENSIVE CATEGORICAL TESTING")
print("="*90)

s2_categories = {
    'productType': {
        'values': ['S2MSI1C', 'S2MSI2A', 'S2MSI2B'],
        'date': ('2016-01-01', '2016-01-31')
    },
    'platformSerialIdentifier': {
        'values': ['A', 'B'],
        'date': ('2016-01-01', '2016-01-31')
    },
    'instrumentShortName': {
        'values': ['MSI'],
        'date': ('2016-01-01', '2016-01-31')
    },
    'processingLevel': {
        'values': ['L1C', 'L2A', 'LEVEL1C', 'LEVEL2A', '1', '2'],
        'date': ('2016-01-01', '2016-01-31')
    },
    'operationalMode': {
        'values': ['INS-NOBS', 'INS-RAW', 'INS-VIC'],
        'date': ('2016-01-01', '2016-01-31')
    },
    'qualityStatus': {
        'values': ['PASSED', 'FAILED', 'DEGRADED'],
        'date': ('2016-01-01', '2016-01-31')
    }
}

s2_results = {}
for attr_name, config in s2_categories.items():
    print(f"\n{attr_name}:")
    s2_results[attr_name] = {'working': [], 'no_results': [], 'errors': []}
    
    for value in config['values']:
        start, end = config['date']
        count, error = test_attribute('SENTINEL-2', 'S2MSI1C', attr_name, value, start, end)
        
        if count > 0:
            print(f"  ✓ {value}: {count} results")
            s2_results[attr_name]['working'].append((value, count))
        elif error:
            print(f"  ✗ {value}: ERROR - {error}")
            s2_results[attr_name]['errors'].append((value, error))
        else:
            print(f"  ⚠ {value}: 0 results")
            s2_results[attr_name]['no_results'].append(value)
        
        time.sleep(0.05)

# ============================================================================
# SENTINEL-3 COMPREHENSIVE TESTING
# ============================================================================
print("\n" + "="*90)
print("SENTINEL-3 - COMPREHENSIVE CATEGORICAL TESTING")
print("="*90)

s3_categories = {
    'instrumentShortName': {
        'values': ['OLCI', 'SLSTR', 'SRAL'],
        'date': ('2016-06-01', '2016-06-30')
    },
    'platformSerialIdentifier': {
        'values': ['A', 'B'],
        'date': ('2016-06-01', '2016-06-30')
    },
    'processingLevel': {
        'values': ['1', '2', 'L1', 'L2', 'LEVEL1', 'LEVEL2'],
        'date': ('2016-06-01', '2016-06-30')
    },
    'timeliness': {
        'values': ['NR', 'NT', 'ST', 'NRT', 'NTC'],
        'date': ('2016-06-01', '2016-06-30')
    },
    'orbitDirection': {
        'values': ['ASCENDING', 'DESCENDING'],
        'date': ('2016-06-01', '2016-06-30')
    }
}

s3_results = {}
for attr_name, config in s3_categories.items():
    print(f"\n{attr_name}:")
    s3_results[attr_name] = {'working': [], 'no_results': [], 'errors': []}
    
    for value in config['values']:
        start, end = config['date']
        # For instrument test, don't specify product_type
        count, error = test_attribute('SENTINEL-3', None, attr_name, value, start, end,
                                     extra_attrs={'instrumentShortName': 'OLCI'} if attr_name != 'instrumentShortName' else None)
        
        if count > 0:
            print(f"  ✓ {value}: {count} results")
            s3_results[attr_name]['working'].append((value, count))
        elif error:
            print(f"  ✗ {value}: ERROR - {error}")
            s3_results[attr_name]['errors'].append((value, error))
        else:
            print(f"  ⚠ {value}: 0 results")
            s3_results[attr_name]['no_results'].append(value)
        
        time.sleep(0.05)

# ============================================================================
# COMPREHENSIVE SUMMARY
# ============================================================================
print("\n" + "="*90)
print("COMPREHENSIVE TEST SUMMARY")
print("="*90)

def print_collection_summary(collection_name, results):
    print(f"\n{collection_name}:")
    print("="*90)
    
    for attr_name, data in results.items():
        working_count = len(data['working'])
        no_results_count = len(data['no_results'])
        error_count = len(data['errors'])
        total = working_count + no_results_count + error_count
        
        print(f"\n  {attr_name} ({working_count}/{total} working):")
        
        if data['working']:
            print(f"    ✓ Working values: {', '.join([v for v, _ in data['working']])}")
        
        if data['no_results']:
            print(f"    ⚠ No results: {', '.join(data['no_results'])}")
        
        if data['errors']:
            print(f"    ✗ Errors: {', '.join([v for v, _ in data['errors']])}")

print_collection_summary("SENTINEL-1", s1_results)
print_collection_summary("SENTINEL-2", s2_results)
print_collection_summary("SENTINEL-3", s3_results)

# Generate documentation-ready summary
print("\n" + "="*90)
print("DOCUMENTATION-READY SUMMARY")
print("="*90)

print("\n## Sentinel-1 Verified Values ##\n")
for attr_name, data in s1_results.items():
    if data['working']:
        values = ', '.join([f"'{v}'" for v, _ in data['working']])
        print(f"**{attr_name}:** {values}")

print("\n## Sentinel-2 Verified Values ##\n")
for attr_name, data in s2_results.items():
    if data['working']:
        values = ', '.join([f"'{v}'" for v, _ in data['working']])
        print(f"**{attr_name}:** {values}")

print("\n## Sentinel-3 Verified Values ##\n")
for attr_name, data in s3_results.items():
    if data['working']:
        values = ', '.join([f"'{v}'" for v, _ in data['working']])
        print(f"**{attr_name}:** {values}")
