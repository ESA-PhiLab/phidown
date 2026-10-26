"""Live check of the STAC product search against CDSE.

Run it on a machine with internet access:

    python examples/stac_live_check.py

It runs a few searches and prints the mapped columns, so you can confirm that
the STAC collection ids and property names match what CDSE serves.
"""

from phidown.search import CopernicusDataSearcher

AOI = "POLYGON((12.4 41.8, 12.6 41.8, 12.6 42.0, 12.4 42.0, 12.4 41.8))"
CASES = [
    dict(collection_name="SENTINEL-1", product_type="SLC", orbit_direction="DESCENDING"),
    dict(collection_name="SENTINEL-1", product_type="GRD"),
    dict(collection_name="SENTINEL-1", product_type="GRD", attributes={"platformSerialIdentifier": "A", "polarisationChannels": "VV&VH"}),
    dict(collection_name="SENTINEL-2", product_type="S2MSI1C", attributes={"tileId": "33TUG"}),
    dict(collection_name="SENTINEL-2", product_type="S2MSI2A", cloud_cover_threshold=20),
    dict(collection_name="SENTINEL-3", product_type="S3OLCI", attributes={"productType": "OL_2_LFR___"}),
    # timeliness and orbitNumber are not STAC queryables: checked on the client.
    dict(collection_name="SENTINEL-3", product_type="S3OLCI", orbit_direction="DESCENDING",
         attributes={"productType": "OL_2_LFR___", "timeliness": "NT", "orbitNumber": 31935}),
    dict(collection_name="SENTINEL-1", orbit_direction="ASCENDING", order_by="ContentDate/Start desc"),
]

for case in CASES:
    searcher = CopernicusDataSearcher()
    searcher.query_by_filter(aoi_wkt=AOI, start_date="2024-06-01T00:00:00", end_date="2024-06-15T00:00:00", top=3, **case)
    df = searcher.execute_query()
    print(f"\n{case} -> {len(df)} rows, STAC body: {searcher.query}")
    if not df.empty:
        print(df[["Name", "Collection", "S3Path", "ContentLength", "coverage"]].to_string(index=False))
        name = df.iloc[0]["Name"]
        found = CopernicusDataSearcher().query_by_name(name)
        print("query_by_name:", len(found), "row(s) for", name, "->", list(found["Name"]) if len(found) else [])
