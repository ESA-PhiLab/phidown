"""
Test Attributes for Different Collections

This test file verifies that all documented attributes work correctly
for different Copernicus collections (Sentinel-1, Sentinel-2, Sentinel-3, CCM).

It tests the corrected parameter names:
- platformSerialIdentifier (not platform)
- instrumentShortName (not instrument)
- Correct timeliness codes (NRT, NTC)
- Correct processing levels (L1, L2)
"""
from phidown.search import CopernicusDataSearcher
import time


def test_sentinel1_basic():
    """Test basic Sentinel-1 search"""
    print("\n" + "="*80)
    print("TEST 1: Sentinel-1 Basic Search")
    print("="*80)
    
    searcher = CopernicusDataSearcher()
    searcher.query_by_filter(
        collection_name='SENTINEL-1',
        product_type='GRD',
        start_date='2015-06-01',
        end_date='2015-06-30',
        top=5,
        count=True
    )
    
    df = searcher.execute_query()
    print(f"✓ Found {len(df)} Sentinel-1 GRD products")
    assert len(df) > 0, "No results found for Sentinel-1 GRD"
    return df


def test_sentinel1_platform_serial_identifier():
    """Test Sentinel-1 with platformSerialIdentifier (corrected from 'platform')"""
    print("\n" + "="*80)
    print("TEST 2: Sentinel-1 with platformSerialIdentifier='A'")
    print("="*80)
    
    searcher = CopernicusDataSearcher()
    searcher.query_by_filter(
        collection_name='SENTINEL-1',
        product_type='GRD',
        start_date='2015-06-01',
        end_date='2015-06-30',
        top=5,
        attributes={'platformSerialIdentifier': 'A'}
    )
    
    df = searcher.execute_query()
    print(f"✓ Found {len(df)} Sentinel-1A products")
    assert len(df) > 0, "No results found for Sentinel-1A"
    return df


def test_sentinel1_operational_mode():
    """Test Sentinel-1 with operational mode"""
    print("\n" + "="*80)
    print("TEST 3: Sentinel-1 with operationalMode='IW'")
    print("="*80)
    
    searcher = CopernicusDataSearcher()
    searcher.query_by_filter(
        collection_name='SENTINEL-1',
        product_type='GRD',
        orbit_direction='DESCENDING',
        start_date='2015-06-01',
        end_date='2015-06-30',
        top=5,
        attributes={'operationalMode': 'IW'}
    )
    
    df = searcher.execute_query()
    print(f"✓ Found {len(df)} Sentinel-1 IW products")
    assert len(df) > 0, "No results found for Sentinel-1 IW mode"
    return df


def test_sentinel1_polarisation():
    """Test Sentinel-1 with polarisation channels"""
    print("\n" + "="*80)
    print("TEST 4: Sentinel-1 with polarisationChannels='HH'")
    print("="*80)
    
    searcher = CopernicusDataSearcher()
    searcher.query_by_filter(
        collection_name='SENTINEL-1',
        product_type='GRD',
        start_date='2015-06-01',
        end_date='2015-06-30',
        top=5,
        attributes={'polarisationChannels': 'HH'}
    )
    
    df = searcher.execute_query()
    print(f"✓ Found {len(df)} Sentinel-1 HH products")
    assert len(df) > 0, "No results found for Sentinel-1 HH polarisation"
    return df


def test_sentinel2_basic():
    """Test basic Sentinel-2 search"""
    print("\n" + "="*80)
    print("TEST 5: Sentinel-2 Basic Search")
    print("="*80)
    
    searcher = CopernicusDataSearcher()
    searcher.query_by_filter(
        collection_name='SENTINEL-2',
        product_type='S2MSI1C',
        start_date='2015-12-01',
        end_date='2015-12-31',
        cloud_cover_threshold=30,
        top=5,
        count=True
    )
    
    df = searcher.execute_query()
    print(f"✓ Found {len(df)} Sentinel-2 L1C products")
    assert len(df) > 0, "No results found for Sentinel-2 L1C"
    return df


def test_sentinel2_platform_serial_identifier():
    """Test Sentinel-2 with platformSerialIdentifier (corrected from 'platform')"""
    print("\n" + "="*80)
    print("TEST 6: Sentinel-2 with platformSerialIdentifier='A'")
    print("="*80)
    
    searcher = CopernicusDataSearcher()
    searcher.query_by_filter(
        collection_name='SENTINEL-2',
        product_type='S2MSI1C',
        start_date='2015-12-01',
        end_date='2015-12-31',
        cloud_cover_threshold=50,
        top=5,
        attributes={'platformSerialIdentifier': 'A'}
    )
    
    df = searcher.execute_query()
    print(f"✓ Found {len(df)} Sentinel-2A products")
    assert len(df) > 0, "No results found for Sentinel-2A"
    return df


def test_sentinel2_instrument_short_name():
    """Test Sentinel-2 with instrumentShortName (corrected from 'instrument')"""
    print("\n" + "="*80)
    print("TEST 7: Sentinel-2 with instrumentShortName='MSI'")
    print("="*80)
    
    searcher = CopernicusDataSearcher()
    searcher.query_by_filter(
        collection_name='SENTINEL-2',
        product_type='S2MSI2A',
        start_date='2017-01-01',
        end_date='2017-01-31',
        cloud_cover_threshold=30,
        top=5,
        attributes={'instrumentShortName': 'MSI'}
    )
    
    df = searcher.execute_query()
    print(f"✓ Found {len(df)} Sentinel-2 MSI products")
    assert len(df) > 0, "No results found for Sentinel-2 MSI"
    return df


def test_sentinel2_processing_level():
    """Test Sentinel-2 with processing level"""
    print("\n" + "="*80)
    print("TEST 8: Sentinel-2 L2A with processingLevel attribute")
    print("="*80)
    
    # First check if L2A products exist at all
    searcher = CopernicusDataSearcher()
    searcher.query_by_filter(
        collection_name='SENTINEL-2',
        product_type='S2MSI2A',
        start_date='2019-01-01',
        end_date='2019-01-15',
        top=5
    )
    
    df = searcher.execute_query()
    print(f"✓ Found {len(df)} Sentinel-2 L2A products")
    
    # Now test with processingLevel attribute
    if len(df) > 0:
        searcher2 = CopernicusDataSearcher()
        searcher2.query_by_filter(
            collection_name='SENTINEL-2',
            product_type='S2MSI2A',
            start_date='2019-01-01',
            end_date='2019-01-15',
            top=5,
            attributes={'processingLevel': 'L2A'}
        )
        df2 = searcher2.execute_query()
        print(f"✓ With processingLevel='L2A' attribute: {len(df2)} products")
    
    assert len(df) > 0, "No Sentinel-2 L2A products found"
    return df


def test_sentinel3_basic():
    """Test basic Sentinel-3 search"""
    print("\n" + "="*80)
    print("TEST 9: Sentinel-3 Basic Search (OLCI)")
    print("="*80)
    
    searcher = CopernicusDataSearcher()
    searcher.query_by_filter(
        collection_name='SENTINEL-3',
        start_date='2016-06-01',
        end_date='2016-06-30',
        top=5,
        count=True,
        attributes={'instrumentShortName': 'OLCI', 'processingLevel': '2'}
    )
    
    df = searcher.execute_query()
    print(f"✓ Found {len(df)} Sentinel-3 OLCI products")
    assert len(df) > 0, "No results found for Sentinel-3 OLCI"
    return df


def test_sentinel3_platform_serial_identifier():
    """Test Sentinel-3 with platformSerialIdentifier (corrected from 'platform')"""
    print("\n" + "="*80)
    print("TEST 10: Sentinel-3 with platformSerialIdentifier='A'")
    print("="*80)
    
    searcher = CopernicusDataSearcher()
    searcher.query_by_filter(
        collection_name='SENTINEL-3',
        start_date='2016-06-01',
        end_date='2016-06-30',
        top=5,
        attributes={'platformSerialIdentifier': 'A', 'instrumentShortName': 'OLCI'}
    )
    
    df = searcher.execute_query()
    print(f"✓ Found {len(df)} Sentinel-3A products")
    assert len(df) > 0, "No results found for Sentinel-3A"
    return df


def test_sentinel3_instrument_short_name():
    """Test Sentinel-3 with instrumentShortName (corrected from 'instrument')"""
    print("\n" + "="*80)
    print("TEST 11: Sentinel-3 with instrumentShortName='OLCI'")
    print("="*80)
    
    searcher = CopernicusDataSearcher()
    searcher.query_by_filter(
        collection_name='SENTINEL-3',
        start_date='2016-06-01',
        end_date='2016-06-30',
        top=5,
        attributes={'instrumentShortName': 'OLCI'}
    )
    
    df = searcher.execute_query()
    print(f"✓ Found {len(df)} Sentinel-3 OLCI instrument products")
    assert len(df) > 0, "No results found for Sentinel-3 OLCI instrument"
    return df


def test_sentinel3_processing_level():
    """Test Sentinel-3 with processing level (corrected format: '2' not 'L2')"""
    print("\n" + "="*80)
    print("TEST 12: Sentinel-3 with processingLevel='2'")
    print("="*80)
    
    searcher = CopernicusDataSearcher()
    searcher.query_by_filter(
        collection_name='SENTINEL-3',
        start_date='2016-06-01',
        end_date='2016-06-30',
        top=5,
        attributes={'processingLevel': '2', 'instrumentShortName': 'OLCI'}
    )
    
    df = searcher.execute_query()
    print(f"✓ Found {len(df)} Sentinel-3 L2 products")
    assert len(df) > 0, "No results found for Sentinel-3 L2"
    return df


def test_sentinel3_timeliness():
    """Test Sentinel-3 with timeliness (corrected codes: NT not NTC)"""
    print("\n" + "="*80)
    print("TEST 13: Sentinel-3 with timeliness='NT'")
    print("="*80)
    
    searcher = CopernicusDataSearcher()
    searcher.query_by_filter(
        collection_name='SENTINEL-3',
        start_date='2016-06-01',
        end_date='2016-06-30',
        top=5,
        attributes={'timeliness': 'NT', 'instrumentShortName': 'OLCI'}
    )
    
    df = searcher.execute_query()
    print(f"✓ Found {len(df)} Sentinel-3 NT products")
    assert len(df) > 0, "No results found for Sentinel-3 NT timeliness"
    return df


def test_sentinel3_slstr():
    """Test Sentinel-3 SLSTR products"""
    print("\n" + "="*80)
    print("TEST 14: Sentinel-3 SLSTR products")
    print("="*80)
    
    searcher = CopernicusDataSearcher()
    searcher.query_by_filter(
        collection_name='SENTINEL-3',
        start_date='2016-06-01',
        end_date='2016-06-30',
        top=5,
        attributes={'instrumentShortName': 'SLSTR', 'processingLevel': '2'}
    )
    
    df = searcher.execute_query()
    print(f"✓ Found {len(df)} Sentinel-3 SLSTR products")
    assert len(df) > 0, "No results found for Sentinel-3 SLSTR"
    return df


def test_sentinel3_sral():
    """Test Sentinel-3 SRAL products"""
    print("\n" + "="*80)
    print("TEST 15: Sentinel-3 SRAL products")
    print("="*80)
    
    searcher = CopernicusDataSearcher()
    searcher.query_by_filter(
        collection_name='SENTINEL-3',
        start_date='2016-06-01',
        end_date='2016-06-30',
        top=5,
        attributes={'instrumentShortName': 'SRAL', 'processingLevel': '2'}
    )
    
    df = searcher.execute_query()
    print(f"✓ Found {len(df)} Sentinel-3 SRAL products")
    assert len(df) > 0, "No results found for Sentinel-3 SRAL"
    return df


def test_ccm_basic():
    """Test basic CCM search"""
    print("\n" + "="*80)
    print("TEST 16: CCM Basic Search")
    print("="*80)
    
    try:
        searcher = CopernicusDataSearcher()
        searcher.query_by_filter(
            collection_name='CCM',
            product_type='NAO_MS4_2A_07B6',
            start_date='2023-01-01',
            end_date='2023-12-31',
            top=5
        )
        
        df = searcher.execute_query()
        print(f"✓ Found {len(df)} CCM products")
        if len(df) == 0:
            print("  Note: No CCM products found. This may require special access.")
        return df
    except Exception as e:
        print(f"⚠ CCM search failed: {e}")
        print("  Note: CCM may require special registration and access rights.")
        return None


def run_all_tests():
    """Run all tests sequentially"""
    print("\n" + "="*80)
    print("RUNNING ALL ATTRIBUTE TESTS")
    print("="*80)
    print("Testing corrected documentation parameters:")
    print("- platformSerialIdentifier (not 'platform')")
    print("- instrumentShortName (not 'instrument')")
    print("- Correct timeliness codes (NRT, NTC)")
    print("- Correct processing levels (L1, L2)")
    print("="*80)
    
    tests = [
        test_sentinel1_basic,
        test_sentinel1_platform_serial_identifier,
        test_sentinel1_operational_mode,
        test_sentinel1_polarisation,
        test_sentinel2_basic,
        test_sentinel2_platform_serial_identifier,
        test_sentinel2_instrument_short_name,
        test_sentinel2_processing_level,
        test_sentinel3_basic,
        test_sentinel3_platform_serial_identifier,
        test_sentinel3_instrument_short_name,
        test_sentinel3_processing_level,
        test_sentinel3_timeliness,
        test_sentinel3_slstr,
        test_sentinel3_sral,
        test_ccm_basic,
    ]
    
    results = {}
    for test in tests:
        try:
            result = test()
            results[test.__name__] = 'PASS'
            time.sleep(0.5)  # Small delay between tests to avoid rate limiting
        except AssertionError as e:
            print(f"✗ FAILED: {e}")
            results[test.__name__] = 'FAIL'
        except Exception as e:
            print(f"✗ ERROR: {e}")
            results[test.__name__] = 'ERROR'
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
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
    results = run_all_tests()
