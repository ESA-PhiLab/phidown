#!/usr/bin/env python3
"""Test search to diagnose the issue."""

from phidown import CopernicusDataSearcher

AOI_WKT = '''POLYGON((11.809016 57.629964, 12.087897 57.629964, 12.087897 57.768659, 11.809016 57.768659, 11.809016 57.629964))'''

print('='*70)
print('Test 1: Search without filters (as find_optimal_orbit does)')
print('='*70)

searcher = CopernicusDataSearcher()
searcher.query_by_filter(
    collection_name='SENTINEL-1',
    product_type='SLC',
    orbit_direction='DESCENDING',
    aoi_wkt=AOI_WKT,
    start_date='2024-08-03T00:00:00',
    end_date='2024-11-10T00:00:00',
    top=100,
    count=True
)

df = searcher.execute_query()
print(f'Found {len(df)} products')

if not df.empty and 'Attributes' in df.columns:
    def get_attr(attrs, name):
        if isinstance(attrs, list):
            for attr in attrs:
                if attr.get('Name') == name:
                    return attr.get('Value')
        return None
    
    df['rel_orbit'] = df['Attributes'].apply(lambda x: get_attr(x, 'relativeOrbitNumber'))
    df['polarisation'] = df['Attributes'].apply(lambda x: get_attr(x, 'polarisationChannels'))
    
    print('Relative orbits found:', sorted([int(x) for x in df['rel_orbit'].unique() if x]))
    orbit_66_count = len(df[df['rel_orbit'] == '66'])
    print(f'Products with orbit 66: {orbit_66_count}')
    print('Polarisations found:', df['polarisation'].unique())
    
    print('\\nSample product with orbit 66:')
    orbit_66 = df[df['rel_orbit'] == '66']
    if not orbit_66.empty:
        print(f"  Name: {orbit_66.iloc[0]['Name']}")
        print(f"  Polarisation: {orbit_66.iloc[0]['polarisation']}")

print('\\n' + '='*70)
print('Test 2: Search with relativeOrbitNumber attribute filter')
print('='*70)

searcher2 = CopernicusDataSearcher()
searcher2.query_by_filter(
    collection_name='SENTINEL-1',
    product_type='SLC',
    orbit_direction='DESCENDING',
    aoi_wkt=AOI_WKT,
    start_date='2024-08-03T00:00:00',
    end_date='2024-11-10T00:00:00',
    attributes={'relativeOrbitNumber': '66'},
    top=100,
    count=True
)

df2 = searcher2.execute_query()
print(f'Found {len(df2)} products')

print('\\n' + '='*70)
print('Test 3: Search with relativeOrbitNumber AND polarisationChannels')
print('='*70)

searcher3 = CopernicusDataSearcher()
searcher3.query_by_filter(
    collection_name='SENTINEL-1',
    product_type='SLC',
    orbit_direction='DESCENDING',
    aoi_wkt=AOI_WKT,
    start_date='2024-08-03T00:00:00',
    end_date='2024-11-10T00:00:00',
    attributes={'relativeOrbitNumber': '66', 'polarisationChannels': 'VV'},
    top=100,
    count=True
)

df3 = searcher3.execute_query()
print(f'Found {len(df3)} products')
