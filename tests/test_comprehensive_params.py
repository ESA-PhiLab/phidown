"""
Comprehensive parameter verification tests

This tests ALL documented parameters to ensure they work correctly.
"""
from phidown.search import CopernicusDataSearcher
import time


print("="*80)
print("COMPREHENSIVE PARAMETER VERIFICATION")
print("="*80)
print("Testing ALL documented parameters for correctness\n")


# ==============================================================================
# SENTINEL-1 COMPREHENSIVE TESTS
# ==============================================================================

def test_s1_processing_level():
    """Sentinel-1: processingLevel"""
    print("\n[S1] Testing processingLevel='LEVEL1'")
    searcher = CopernicusDataSearcher()
    searcher.query_by_filter(
        collection_name='SENTINEL-1',
        start_date='2015-06-01',
        end_date='2015-06-05',
        top=3,
        attributes={'processingLevel': 'LEVEL1'}
    )
    df = searcher.execute_query()
    print(f"  ✓ Found {len(df)} products")
    assert len(df) > 0
    return df


def test_s1_swath_identifier():
    """Sentinel-1: swathIdentifier"""
    print("\n[S1] Testing swathIdentifier='IW'")
    searcher = CopernicusDataSearcher()
    searcher.query_by_filter(
        collection_name='SENTINEL-1',
        start_date='2015-06-01',
        end_date='2015-06-05',
        top=3,
        attributes={'swathIdentifier': 'IW'}
    )
    df = searcher.execute_query()
    print(f"  ✓ Found {len(df)} products")
    assert len(df) > 0
    return df


def test_s1_instrument_short_name():
    """Sentinel-1: instrumentShortName (not 'instrument')"""
    print("\n[S1] Testing instrumentShortName='SAR' (corrected from 'instrument')")
    searcher = CopernicusDataSearcher()
    searcher.query_by_filter(
        collection_name='SENTINEL-1',
        start_date='2015-06-01',
        end_date='2015-06-05',
        top=3,
        attributes={'instrumentShortName': 'SAR'}
    )
    df = searcher.execute_query()
    print(f"  ✓ Found {len(df)} products")
    assert len(df) > 0
    return df


def test_s1_orbit_number():
    """Sentinel-1: orbitNumber"""
    print("\n[S1] Testing orbitNumber (range query)")
    searcher = CopernicusDataSearcher()
    searcher.query_by_filter(
        collection_name='SENTINEL-1',
        product_type='GRD',
        start_date='2015-06-01',
        end_date='2015-06-30',
        top=3,
        attributes={'orbitNumber': '[6200,6300]'}
    )
    df = searcher.execute_query()
    print(f"  ✓ Found {len(df)} products")
    assert len(df) > 0
    return df


def test_s1_relative_orbit_number():
    """Sentinel-1: relativeOrbitNumber"""
    print("\n[S1] Testing relativeOrbitNumber='33'")
    searcher = CopernicusDataSearcher()
    searcher.query_by_filter(
        collection_name='SENTINEL-1',
        product_type='GRD',
        start_date='2015-06-01',
        end_date='2015-06-30',
        top=3,
        attributes={'relativeOrbitNumber': '33'}
    )
    df = searcher.execute_query()
    print(f"  ✓ Found {len(df)} products")
    assert len(df) > 0
    return df


def test_s1_timeliness():
    """Sentinel-1: timeliness"""
    print("\n[S1] Testing timeliness='Fast-24h'")
    searcher = CopernicusDataSearcher()
    searcher.query_by_filter(
        collection_name='SENTINEL-1',
        product_type='GRD',
        start_date='2015-06-01',
        end_date='2015-06-30',
        top=3,
        attributes={'timeliness': 'Fast-24h'}
    )
    df = searcher.execute_query()
    print(f"  ✓ Found {len(df)} products")
    assert len(df) > 0
    return df


# ==============================================================================
# SENTINEL-2 COMPREHENSIVE TESTS
# ==============================================================================

def test_s2_tile_id():
    """Sentinel-2: tileId"""
    print("\n[S2] Testing tileId")
    searcher = CopernicusDataSearcher()
    searcher.query_by_filter(
        collection_name='SENTINEL-2',
        product_type='S2MSI1C',
        start_date='2016-01-01',
        end_date='2016-01-31',
        top=3,
        attributes={'tileId': '33UUP'}
    )
    df = searcher.execute_query()
    print(f"  ✓ Found {len(df)} products")
    assert len(df) > 0
    return df


def test_s2_cloud_cover_range():
    """Sentinel-2: cloudCover with range"""
    print("\n[S2] Testing cloudCover='[0,20]'")
    searcher = CopernicusDataSearcher()
    searcher.query_by_filter(
        collection_name='SENTINEL-2',
        product_type='S2MSI1C',
        start_date='2016-01-01',
        end_date='2016-01-31',
        top=3,
        attributes={'cloudCover': '[0,20]'}
    )
    df = searcher.execute_query()
    print(f"  ✓ Found {len(df)} products")
    assert len(df) > 0
    return df


def test_s2_orbit_number():
    """Sentinel-2: orbitNumber"""
    print("\n[S2] Testing orbitNumber (range)")
    searcher = CopernicusDataSearcher()
    searcher.query_by_filter(
        collection_name='SENTINEL-2',
        product_type='S2MSI1C',
        start_date='2016-01-01',
        end_date='2016-01-31',
        top=3,
        attributes={'orbitNumber': '[1000,2000]'}
    )
    df = searcher.execute_query()
    print(f"  ✓ Found {len(df)} products")
    assert len(df) > 0
    return df


def test_s2_relative_orbit_number():
    """Sentinel-2: relativeOrbitNumber"""
    print("\n[S2] Testing relativeOrbitNumber='51'")
    searcher = CopernicusDataSearcher()
    searcher.query_by_filter(
        collection_name='SENTINEL-2',
        product_type='S2MSI1C',
        start_date='2016-01-01',
        end_date='2016-01-31',
        top=3,
        attributes={'relativeOrbitNumber': '51'}
    )
    df = searcher.execute_query()
    print(f"  ✓ Found {len(df)} products")
    assert len(df) > 0
    return df


# ==============================================================================
# SENTINEL-3 COMPREHENSIVE TESTS
# ==============================================================================

def test_s3_orbit_direction():
    """Sentinel-3: orbitDirection"""
    print("\n[S3] Testing orbitDirection='ASCENDING'")
    searcher = CopernicusDataSearcher()
    searcher.query_by_filter(
        collection_name='SENTINEL-3',
        orbit_direction='ASCENDING',
        start_date='2016-06-01',
        end_date='2016-06-05',
        top=3,
        attributes={'instrumentShortName': 'OLCI'}
    )
    df = searcher.execute_query()
    print(f"  ✓ Found {len(df)} products")
    assert len(df) > 0
    return df


def test_s3_orbit_number():
    """Sentinel-3: orbitNumber"""
    print("\n[S3] Testing orbitNumber (range)")
    searcher = CopernicusDataSearcher()
    searcher.query_by_filter(
        collection_name='SENTINEL-3',
        start_date='2016-06-01',
        end_date='2016-06-30',
        top=3,
        attributes={'orbitNumber': '[4500,4600]', 'instrumentShortName': 'SRAL'}
    )
    df = searcher.execute_query()
    print(f"  ✓ Found {len(df)} products")
    assert len(df) > 0
    return df


def test_s3_relative_orbit_number():
    """Sentinel-3: relativeOrbitNumber"""
    print("\n[S3] Testing relativeOrbitNumber")
    searcher = CopernicusDataSearcher()
    searcher.query_by_filter(
        collection_name='SENTINEL-3',
        start_date='2016-06-01',
        end_date='2016-06-30',
        top=3,
        attributes={'relativeOrbitNumber': '329', 'instrumentShortName': 'SRAL'}
    )
    df = searcher.execute_query()
    print(f"  ✓ Found {len(df)} products")
    assert len(df) > 0
    return df


def test_s3_cloud_cover():
    """Sentinel-3: cloudCover"""
    print("\n[S3] Testing cloudCover='[0,30]'")
    searcher = CopernicusDataSearcher()
    searcher.query_by_filter(
        collection_name='SENTINEL-3',
        start_date='2016-06-01',
        end_date='2016-06-30',
        top=3,
        attributes={'cloudCover': '[0,30]', 'instrumentShortName': 'OLCI', 'processingLevel': '2'}
    )
    df = searcher.execute_query()
    print(f"  ✓ Found {len(df)} products")
    assert len(df) > 0
    return df


def test_s3_cycle_number():
    """Sentinel-3: cycleNumber"""
    print("\n[S3] Testing cycleNumber='12'")
    searcher = CopernicusDataSearcher()
    searcher.query_by_filter(
        collection_name='SENTINEL-3',
        start_date='2016-12-01',
        end_date='2016-12-31',
        top=3,
        attributes={'cycleNumber': '12', 'instrumentShortName': 'SRAL'}
    )
    df = searcher.execute_query()
    print(f"  ✓ Found {len(df)} products")
    assert len(df) > 0
    return df


# ==============================================================================
# RUN ALL TESTS
# ==============================================================================

def run_all_comprehensive_tests():
    """Run all comprehensive parameter tests"""
    tests = [
        # Sentinel-1
        ('S1 processingLevel', test_s1_processing_level),
        ('S1 swathIdentifier', test_s1_swath_identifier),
        ('S1 instrumentShortName', test_s1_instrument_short_name),
        ('S1 orbitNumber', test_s1_orbit_number),
        ('S1 relativeOrbitNumber', test_s1_relative_orbit_number),
        ('S1 timeliness', test_s1_timeliness),
        
        # Sentinel-2
        ('S2 tileId', test_s2_tile_id),
        ('S2 cloudCover', test_s2_cloud_cover_range),
        ('S2 orbitNumber', test_s2_orbit_number),
        ('S2 relativeOrbitNumber', test_s2_relative_orbit_number),
        
        # Sentinel-3
        ('S3 orbitDirection', test_s3_orbit_direction),
        ('S3 orbitNumber', test_s3_orbit_number),
        ('S3 relativeOrbitNumber', test_s3_relative_orbit_number),
        ('S3 cloudCover', test_s3_cloud_cover),
        ('S3 cycleNumber', test_s3_cycle_number),
    ]
    
    results = {}
    for name, test_func in tests:
        try:
            test_func()
            results[name] = 'PASS'
            time.sleep(0.3)
        except AssertionError as e:
            print(f"  ✗ FAILED: {e}")
            results[name] = 'FAIL'
        except Exception as e:
            print(f"  ✗ ERROR: {e}")
            results[name] = 'ERROR'
    
    # Summary
    print("\n" + "="*80)
    print("COMPREHENSIVE TEST SUMMARY")
    print("="*80)
    passed = sum(1 for v in results.values() if v == 'PASS')
    failed = sum(1 for v in results.values() if v == 'FAIL')
    errors = sum(1 for v in results.values() if v == 'ERROR')
    
    for test_name, status in results.items():
        symbol = '✓' if status == 'PASS' else '✗'
        print(f"{symbol} {test_name}: {status}")
    
    print(f"\nTotal: {len(tests)} tests")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Errors: {errors}")
    print("="*80)
    
    return results


if __name__ == '__main__':
    results = run_all_comprehensive_tests()
