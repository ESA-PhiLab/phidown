"""Unit tests for the STAC product search.

The STAC responses below are fixed fixtures shaped like CDSE STAC items.
They do not replace a live check against https://stac.dataspace.copernicus.eu.
"""

from unittest.mock import Mock, patch

import pytest
import requests

from phidown import stac
from phidown.search import CopernicusDataSearcher

# Real collection ids from https://stac.dataspace.copernicus.eu/v1/collections (subset).
COLLECTIONS = [
    "sentinel-1-etad", "sentinel-1-global-mosaics", "sentinel-1-grd", "sentinel-1-ocn", "sentinel-1-slc",
    "sentinel-1-slc-burst", "sentinel-1-slc-wv", "sentinel-2-global-mosaics", "sentinel-2-gri-l1c",
    "sentinel-2-l1c", "sentinel-2-l2a", "sentinel-2-l2a-tlm", "sentinel-3-olci-2-lfr-nrt",
    "sentinel-3-olci-2-lfr-ntc", "sentinel-3-sr-1-sra-a-ntc", "sentinel-3-sr-1-sra-ntc",
    "sentinel-5p-l2-no2", "sentinel-5p-l2-no2-offl", "sentinel-5p-l2-no2-nrti",
    "cop-dem-eea-10-laea-tif", "cop-dem-glo-30-dged-cog", "cop-dem-glo-90-dged-cog",
]
S1_DEFAULT = ["sentinel-1-etad", "sentinel-1-grd", "sentinel-1-ocn", "sentinel-1-slc", "sentinel-1-slc-wv"]
PRODUCT = "S1A_IW_SLC__1SDV_20240102T030405_20240102T030432_052000_064A1B_ABCD"
UUID = "0f5d2c3e-1111-2222-3333-444455556666"


def _item(name=PRODUCT, collection="sentinel-1-slc", start="2024-01-02T03:04:05Z"):
    """An item shaped like a CDSE sentinel-1-slc item (2026-10)."""
    return {
        "type": "Feature",
        "id": name,
        "collection": collection,
        "geometry": {"type": "Polygon", "coordinates": [[[10, 40], [11, 40], [11, 41], [10, 41], [10, 40]]]},
        "properties": {
            "_private": {"visible": True, "product_name": f"{name}.SAFE", "product_size": 4199990000, "product_uuid": UUID},
            "datetime": start,
            "platform": "sentinel-1a",
            "start_datetime": start,
            "end_datetime": "2024-01-02T03:04:32Z",
            "product:type": "IW_SLC__1S",
            "sat:orbit_state": "descending",
            "sat:relative_orbit": 117,
            "sar:polarizations": ["VV", "VH"],
            "published": "2024-01-02T05:00:00Z",
            "product:timeliness_category": "NRT-3h",
        },
        "assets": {
            "iw1-vv": {"href": f"s3://eodata/Sentinel-1/SAR/IW_SLC__1S/2024/01/02/{name}.SAFE/measurement/s1a-iw1-slc-vv.tiff"},
            "product": {
                "href": f"https://download.dataspace.copernicus.eu/odata/v1/Products({UUID})/$value",
                "file:size": 4200000000,
            },
            "safe_manifest": {
                "href": f"s3://eodata/Sentinel-1/SAR/IW_SLC__1S/2024/01/02/{name}.SAFE/manifest.safe",
                "alternate": {"https": {"href": f"https://download.dataspace.copernicus.eu/odata/v1/Products({UUID})/Nodes({name}.SAFE)/Nodes(manifest.safe)/$value"}},
            },
        },
    }


def _response(payload, status_code=200, headers=None):
    response = Mock()
    response.status_code = status_code
    response.headers = headers or {}
    response.raise_for_status = Mock()
    response.json.return_value = payload
    return response


def test_wkt_to_geojson_handles_supported_types():
    assert stac.wkt_to_geojson("POINT (10 40)") == {"type": "Point", "coordinates": [10.0, 40.0]}
    assert stac.wkt_to_geojson("POLYGON((10 40, 11 40, 11 41, 10 40))") == {
        "type": "Polygon",
        "coordinates": [[[10.0, 40.0], [11.0, 40.0], [11.0, 41.0], [10.0, 40.0]]],
    }
    multi = stac.wkt_to_geojson("MULTIPOLYGON(((0 0, 1 0, 1 1, 0 0)), ((2 2, 3 2, 3 3, 2 2)))")
    assert multi["type"] == "MultiPolygon" and len(multi["coordinates"]) == 2
    assert stac.wkt_to_geojson("MULTIPOINT((1 2), (3 4))")["coordinates"] == [[1.0, 2.0], [3.0, 4.0]]
    assert stac.wkt_to_geojson("LINESTRING(1 2, 3 4)")["coordinates"] == [[1.0, 2.0], [3.0, 4.0]]


def test_resolve_collections_uses_product_type_suffix():
    assert stac.resolve_collections("SENTINEL-1", "SLC", COLLECTIONS) == (["sentinel-1-slc", "sentinel-1-slc-wv"], True)
    assert stac.resolve_collections("SENTINEL-1", "GRD", COLLECTIONS) == (["sentinel-1-grd"], True)
    assert stac.resolve_collections("SENTINEL-2", "S2MSI1C", COLLECTIONS) == (["sentinel-2-l1c"], True)
    assert stac.resolve_collections("SENTINEL-2", "S2MSI2A", COLLECTIONS) == (["sentinel-2-l2a"], True)
    # Mosaics, bursts and GRI sets are not part of the default set.
    assert stac.resolve_collections("SENTINEL-1", None, COLLECTIONS) == (S1_DEFAULT, False)
    assert stac.resolve_collections("SENTINEL-2", None, COLLECTIONS) == (["sentinel-2-l1c", "sentinel-2-l2a"], False)
    # A full Sentinel-1 type picks the collection and keeps the type filter.
    assert stac.resolve_collections("SENTINEL-1", "IW_SLC__1S", COLLECTIONS) == (["sentinel-1-slc"], False)
    assert stac.resolve_collections("SENTINEL-1", "WV_SLC__1S", COLLECTIONS) == (["sentinel-1-slc-wv"], False)
    with pytest.raises(stac.StacError):
        stac.resolve_collections("ENVISAT", None, COLLECTIONS)


def test_resolve_collections_maps_sentinel3_and_5p_product_types():
    assert stac.resolve_collections("SENTINEL-3", "OL_2_LFR___", COLLECTIONS) == (
        ["sentinel-3-olci-2-lfr-nrt", "sentinel-3-olci-2-lfr-ntc"], True)
    assert stac.resolve_collections("SENTINEL-3", "SR_1_SRA___", COLLECTIONS) == (["sentinel-3-sr-1-sra-ntc"], True)
    assert stac.resolve_collections("SENTINEL-3", "SR_1_SRA_A_", COLLECTIONS) == (["sentinel-3-sr-1-sra-a-ntc"], True)
    # The combined and the timeliness collections cover different dates.
    assert stac.resolve_collections("SENTINEL-5P", "L2__NO2___", COLLECTIONS) == (
        ["sentinel-5p-l2-no2", "sentinel-5p-l2-no2-offl", "sentinel-5p-l2-no2-nrti"], True)
    assert stac.resolve_collections("SENTINEL-3", "S3SRAL", COLLECTIONS) == (
        ["sentinel-3-sr-1-sra-a-ntc", "sentinel-3-sr-1-sra-ntc"], True)


@patch("phidown.stac.list_collections", return_value=COLLECTIONS)
@patch("phidown.stac.requests.post")
def test_searcher_exact_product_type_attribute_narrows_collections(mock_post, _collections):
    mock_post.return_value = _response({"features": [], "links": []})
    searcher = CopernicusDataSearcher()
    searcher.query_by_filter(collection_name="SENTINEL-3", product_type="S3OLCI", attributes={"productType": "OL_2_LFR___"}, top=3)

    searcher.execute_query()

    body = mock_post.call_args.kwargs["json"]
    assert body["collections"] == ["sentinel-3-olci-2-lfr-nrt", "sentinel-3-olci-2-lfr-ntc"]
    assert "filter" not in body


def test_resolve_collections_sentinel1_raw_product_type():
    assert stac.resolve_collections("SENTINEL-1", "IW_RAW__0S", ["sentinel-1-raw"]) == (["sentinel-1-raw"], False)


def test_collections_for_product_name():
    assert stac.collections_for_product_name(PRODUCT, COLLECTIONS) == ["sentinel-1-slc"]
    assert stac.collections_for_product_name("S1A_IW_GRDH_1SDV_20240610T170608_X.SAFE", COLLECTIONS) == ["sentinel-1-grd"]
    assert stac.collections_for_product_name("S2A_MSIL2A_20240613T100031_N0510", COLLECTIONS) == ["sentinel-2-l2a"]
    assert stac.collections_for_product_name(
        "S3B_OL_2_LFR____20240612T092654_20240612T092954_20250720T172843_0179_094_093_2160_ESA_R_NT_003.SEN3", COLLECTIONS
    ) == ["sentinel-3-olci-2-lfr-ntc"]
    assert stac.collections_for_product_name("S1", COLLECTIONS) == S1_DEFAULT
    assert "sentinel-1-slc-burst" not in stac.collections_for_product_name("", COLLECTIONS)


def test_build_search_body_translates_filters():
    body = stac.build_search_body(
        collections=["sentinel-2-l2a"],
        orbit_direction="DESCENDING",
        cloud_cover_threshold=20,
        attributes={"relativeOrbitNumber": 117, "polarisationChannels": "VV&VH", "platformSerialIdentifier": "A", "tileId": "33TUG"},
        aoi_wkt="POINT (10 40)",
        start_date="2024-01-01T00:00:00Z",
        end_date="2024-02-01T00:00:00Z",
        limit=50,
        order_by="ContentDate/Start desc",
    )
    assert body["collections"] == ["sentinel-2-l2a"]
    assert body["limit"] == 50
    assert body["intersects"] == {"type": "Point", "coordinates": [10.0, 40.0]}
    assert body["datetime"] == "2024-01-01T00:00:00Z/2024-02-01T00:00:00Z"
    assert body["sortby"] == [{"field": "start_datetime", "direction": "desc"}]
    assert body["filter-lang"] == "cql2-json"
    assert body["filter"] == {
        "op": "and",
        "args": [
            {"op": "=", "args": [{"property": "sat:orbit_state"}, "descending"]},
            {"op": "<", "args": [{"property": "eo:cloud_cover"}, 20]},
            {"op": "=", "args": [{"property": "sat:relative_orbit"}, 117]},
            {"op": "a_equals", "args": [{"property": "sar:polarizations"}, ["VV", "VH"]]},
            {"op": "=", "args": [{"property": "platform"}, "sentinel-2a"]},
            {"op": "=", "args": [{"property": "grid:code"}, "MGRS-33TUG"]},
        ],
    }


@pytest.mark.parametrize(
    "value, channels",
    [
        ("VV", ["VV"]),
        ("vh", ["VH"]),
        ("VH&VV", ["VV", "VH"]),
        ("HV HH", ["HH", "HV"]),
        ("VV,VV", ["VV"]),
    ],
)
def test_build_search_body_matches_the_exact_polarisation_set(value, channels):
    body = stac.build_search_body(collections=["sentinel-1-grd"], attributes={"polarisationChannels": value})
    assert body["filter"] == {"op": "a_equals", "args": [{"property": "sar:polarizations"}, channels]}


def test_build_search_body_open_date_range_and_no_filter():
    body = stac.build_search_body(collections=["x"], start_date="2024-01-01T00:00:00Z")
    assert body["datetime"] == "2024-01-01T00:00:00Z/.."
    body = stac.build_search_body(collections=["x"], start_date="2024-01-01T00:00:00", end_date="2024-02-01")
    assert body["datetime"] == "2024-01-01T00:00:00Z/2024-02-01T00:00:00Z"
    assert stac.build_search_body(collections=["x"], end_date="2024-02-01T00:00:00+01:00")["datetime"] == "/2024-02-01T00:00:00+01:00"
    assert "filter" not in body


def test_item_to_record_maps_odata_columns():
    record = stac.item_to_record(_item())
    assert record["Id"] == UUID
    assert record["DownloadUrl"].endswith(f"Products({UUID})/$value")
    assert record["Name"] == f"{PRODUCT}.SAFE"
    assert record["S3Path"] == f"/eodata/Sentinel-1/SAR/IW_SLC__1S/2024/01/02/{PRODUCT}.SAFE"
    assert record["ContentLength"] == 4200000000
    assert record["ContentDate"] == {"Start": "2024-01-02T03:04:05Z", "End": "2024-01-02T03:04:32Z"}
    assert record["GeoFootprint"]["type"] == "Polygon"
    assert record["Footprint"].startswith("geography'SRID=4326;POLYGON ((10 40")
    attributes = {item["Name"]: item["Value"] for item in record["Attributes"]}
    assert attributes["productType"] == "IW_SLC__1S"
    assert attributes["orbitDirection"] == "DESCENDING"
    assert attributes["relativeOrbitNumber"] == 117
    assert attributes["platformSerialIdentifier"] == "A"
    assert attributes["timeliness"] == "NRT-3h"
    assert "_private" not in attributes


def test_item_to_record_reads_capitalised_product_asset_and_private_fallbacks():
    item = _item()
    item["assets"]["Product"] = item["assets"].pop("product")
    assert stac.item_to_record(item)["ContentLength"] == 4200000000
    del item["assets"]["Product"]
    record = stac.item_to_record(item)
    assert record["Id"] == UUID
    assert record["ContentLength"] == 4199990000
    assert record["Name"] == f"{PRODUCT}.SAFE"


def test_search_follows_next_links():
    first = _response({"features": [_item("A")], "numberMatched": 3, "links": [
        {"rel": "next", "href": "https://stac/v1/search", "method": "POST", "body": {"token": "p2"}, "merge": True},
    ]})
    second = _response({"features": [_item("B")], "links": [{"rel": "next", "href": "https://stac/v1/search?token=p3"}]})
    third = _response({"features": [_item("C")], "links": []})
    session = Mock()
    session.post.side_effect = [first, second]
    session.get.return_value = third

    items, matched, _ = stac.search({"collections": ["c"], "limit": 1}, max_items=None, session=session)

    assert [item["id"] for item in items] == ["A", "B", "C"]
    assert matched == 3
    assert session.post.call_args_list[1].kwargs["json"] == {"collections": ["c"], "limit": 1, "token": "p2"}
    assert session.get.call_args.args[0] == "https://stac/v1/search?token=p3"


def test_search_reports_rejected_filter_properties():
    rejected = _response({"detail": {
        "code": "FilterValidationError",
        "collections": {"sentinel-1-ocn": {"invalid_attributes": ["sat:orbit_state"]}},
    }}, status_code=400)
    session = Mock()
    session.post.return_value = rejected

    with pytest.raises(stac.StacQueryRejected, match="sat:orbit_state"):
        stac.search({"collections": ["sentinel-1-ocn"]}, max_items=None, session=session)

    assert session.post.call_count == 1


@patch("phidown.stac.time.sleep")
def test_search_retries_rate_limited_requests(mock_sleep):
    session = Mock()
    session.post.side_effect = [
        _response({}, status_code=429, headers={"Retry-After": "1"}),
        _response({"features": [_item("A")], "links": []}),
    ]
    items, _, _ = stac.search({"collections": ["c"]}, max_items=None, session=session)
    assert [item["id"] for item in items] == ["A"]
    mock_sleep.assert_called_once_with(1.0)


def test_search_stops_at_max_items():
    page = _response({"features": [_item("A"), _item("B")], "links": [{"rel": "next", "href": "https://stac/next"}]})
    session = Mock()
    session.post.return_value = page
    items, _, _ = stac.search({}, max_items=1, session=session)
    assert len(items) == 1
    session.get.assert_not_called()


@patch("phidown.stac.list_collections", return_value=COLLECTIONS)
@patch("phidown.stac.requests.post")
def test_searcher_execute_query_uses_stac(mock_post, _collections):
    mock_post.return_value = _response({"features": [_item()], "numberMatched": 1, "links": []})
    searcher = CopernicusDataSearcher()
    searcher.query_by_filter(
        collection_name="SENTINEL-1",
        product_type="SLC",
        orbit_direction="DESCENDING",
        aoi_wkt="POLYGON((10 40, 11 40, 11 41, 10 41, 10 40))",
        start_date="2024-01-01T00:00:00",
        end_date="2024-01-31T00:00:00",
        top=10,
    )

    df = searcher.execute_query()

    body = mock_post.call_args.kwargs["json"]
    assert mock_post.call_args.args[0] == "https://stac.dataspace.copernicus.eu/v1/search"
    assert body["collections"] == ["sentinel-1-slc", "sentinel-1-slc-wv"]
    assert body["limit"] == 10
    assert body["filter"] == {"op": "=", "args": [{"property": "sat:orbit_state"}, "descending"]}
    assert searcher.num_results == 1
    assert list(df["Name"]) == [f"{PRODUCT}.SAFE"]
    assert df["coverage"].iloc[0] in (100.0, None)


@patch("phidown.stac.list_collections", return_value=COLLECTIONS)
@patch("phidown.stac.requests.post")
def test_searcher_skip_drops_leading_items(mock_post, _collections):
    mock_post.return_value = _response({"features": [_item("A"), _item("B"), _item("C")], "links": []})
    searcher = CopernicusDataSearcher()
    searcher.query_by_filter(collection_name="SENTINEL-2", product_type="S2MSI2A", top=2, skip=1)

    df = searcher.execute_query()

    assert mock_post.call_args.kwargs["json"]["limit"] == 3
    assert list(df["StacId"]) == ["B", "C"]


@patch("phidown.stac.list_collections", return_value=COLLECTIONS)
@patch("phidown.stac.requests.post")
def test_query_by_name_searches_item_ids(mock_post, _collections):
    mock_post.return_value = _response({"features": [_item()], "links": []})
    searcher = CopernicusDataSearcher()

    df = searcher.query_by_name(f"{PRODUCT}.SAFE")

    assert mock_post.call_args.kwargs["json"]["ids"] == [PRODUCT]
    assert mock_post.call_args.kwargs["json"]["collections"] == ["sentinel-1-slc"]
    assert df.iloc[0]["S3Path"].endswith(f"{PRODUCT}.SAFE")


def test_list_collections_follows_next_links_and_caches():
    first = _response({"collections": [{"id": "a"}], "links": [{"rel": "next", "href": "https://stac/collections?offset=1"}]})
    second = _response({"collections": [{"id": "b"}], "links": []})
    with patch("phidown.stac.requests.get", side_effect=[first, second]) as mock_get:
        assert stac.list_collections("https://stac") == ["a", "b"]
        assert stac.list_collections("https://stac") == ["a", "b"]
    assert mock_get.call_count == 2
    assert mock_get.call_args_list[0].args[0] == "https://stac/collections?limit=1000"


def test_collections_for_other_product_names():
    assert stac.collections_for_product_name(
        "S5P_OFFL_L2__NO2____20240607T115910_20240607T134040_34463_03_020600_20240612T103851", COLLECTIONS
    ) == ["sentinel-5p-l2-no2", "sentinel-5p-l2-no2-offl"]
    assert stac.collections_for_product_name("Copernicus_DSM_COG_10_N42_00_E012_00_DEM", COLLECTIONS) == [
        "cop-dem-glo-30-dged-cog", "cop-dem-glo-90-dged-cog"]
    assert stac.collections_for_product_name("DEM1_SAR_INS_10_20110207T170647_x", COLLECTIONS) == ["cop-dem-eea-10-laea-tif"]


def test_item_to_record_cuts_s3_path_at_item_folder():
    """Copernicus DEM EEA-10 item shape (2026-10): no extension, deep data asset."""
    item_id = "DEM1_SAR_INS_10_20110207T170647_20140322T165914_ADS_000000_6414_f681a935"
    folder = f"s3://eodata/CCM/COP-DEM_EEA-10-INSP/SAR_INS_10_52C5/2011/02/07/{item_id}"
    item = {
        "id": item_id,
        "properties": {"datetime": "2011-02-07T17:06:49Z"},
        "assets": {
            "data": {"href": f"{folder}/Copernicus_DSM_03_N42_00_E012_00/DEM/Copernicus_DSM_03_N42_00_E012_00_DEM.tif"},
            "product": {"href": f"https://download.dataspace.copernicus.eu/odata/v1/Products({UUID})/$value", "file:size": 1171285320},
            "inspire_metadata": {"href": f"{folder}/INSPIRE.xml"},
        },
    }
    record = stac.item_to_record(item)
    assert record["S3Path"] == folder.replace("s3://", "/")
    assert record["Name"] == item_id
    assert record["ContentLength"] == 1171285320


def test_search_drops_duplicate_items_across_collections():
    page = _response({"features": [_item("A"), _item("A"), _item("B")], "links": []})
    session = Mock()
    session.post.return_value = page
    items, _, _ = stac.search({"collections": ["x", "x-offl"]}, max_items=None, session=session)
    assert [item["id"] for item in items] == ["A", "B"]


def test_item_to_record_size_of_single_file_product():
    """Sentinel-5P item shape (2026-10): one netcdf asset, no product asset."""
    name = "S5P_OFFL_L2__NO2____20240607T115910_20240607T134040_34463_03_020600_20240612T103851"
    href = f"s3://eodata/Sentinel-5P/TROPOMI/L2__NO2___/2024/06/07/{name}.nc"
    record = stac.item_to_record({
        "id": name,
        "properties": {"datetime": "2024-06-07T12:00:00Z"},
        "assets": {"netcdf": {"href": href, "file:size": 616351858}},
    })
    assert record["Name"] == f"{name}.nc"
    assert record["S3Path"] == href.replace("s3://", "/")
    assert record["ContentLength"] == 616351858


def _odata_response(rows):
    return _response({"value": rows, "@odata.count": len(rows)})


@pytest.mark.parametrize(
    "query",
    [
        {"collection_name": "SMOS"},
        {"collection_name": "LANDSAT-8-ESA"},
        {"collection_name": "CCM"},
        {"collection_name": "SENTINEL-1"},
        {"collection_name": "SENTINEL-1", "attributes": {"productType": "IW_RAW__0S"}},
        {"collection_name": "SENTINEL-1", "product_type": "RAW"},
        {"collection_name": "SENTINEL-1", "product_type": "SLC", "attributes": {"processingLevel": "LEVEL1"}},
        {"collection_name": "SENTINEL-2", "attributes": {"instrumentShortName": "MSI"}},
    ],
)
@patch("phidown.stac.requests.post")
def test_queries_stac_cannot_answer_use_odata(mock_post, query):
    with patch("phidown.search.requests.get", return_value=_odata_response([{"Id": "x", "Name": "x"}])) as mock_get:
        searcher = CopernicusDataSearcher()
        searcher.query_by_filter(**query)
        df = searcher.execute_query()
    mock_post.assert_not_called()
    assert "odata/v1/Products" in mock_get.call_args.args[0]
    assert list(df["Id"]) == ["x"]


@patch("phidown.stac.requests.post")
def test_sentinel1_raw_product_type_sends_odata_product_type_filter(mock_post):
    with patch("phidown.search.requests.get", return_value=_odata_response([])) as mock_get:
        searcher = CopernicusDataSearcher()
        searcher.query_by_filter(collection_name="SENTINEL-1", product_type="RAW")
        searcher.execute_query()
    mock_post.assert_not_called()
    url = mock_get.call_args.args[0]
    assert "odata/v1/Products" in url
    assert "att/Name eq 'productType' and att/OData.CSC.StringAttribute/Value eq 'RAW'" in url


@patch("phidown.stac.list_collections", return_value=COLLECTIONS)
@patch("phidown.stac.requests.post")
def test_rejected_stac_filter_falls_back_to_odata(mock_post, _collections):
    mock_post.return_value = _response({"detail": {
        "code": "FilterValidationError",
        "collections": {"sentinel-1-slc": {"invalid_attributes": ["eo:cloud_cover"]}},
    }}, status_code=400)
    with patch("phidown.search.requests.get", return_value=_odata_response([])) as mock_get:
        searcher = CopernicusDataSearcher()
        searcher.query_by_filter(collection_name="SENTINEL-1", product_type="SLC", cloud_cover_threshold=50)
        assert searcher.execute_query().empty
    assert mock_post.call_count == 1
    assert "cloudCover" in mock_get.call_args.args[0]


@patch("phidown.stac.list_collections", return_value=COLLECTIONS)
@patch("phidown.stac.requests.post", side_effect=requests.exceptions.ConnectionError("down"))
def test_stac_outage_falls_back_to_odata(_post, _collections):
    with patch("phidown.search.requests.get", return_value=_odata_response([{"Id": "x"}])):
        searcher = CopernicusDataSearcher()
        searcher.query_by_filter(collection_name="SENTINEL-2", product_type="S2MSI2A")
        assert list(searcher.execute_query()["Id"]) == ["x"]


def test_search_rejects_html_response_as_stac_error():
    html = _response({})
    html.json.side_effect = ValueError("not JSON")
    session = Mock()
    session.post.return_value = html
    with pytest.raises(stac.StacError, match="not JSON"):
        stac.search({"collections": ["x"]}, max_items=None, session=session)


def test_search_retries_timeouts():
    session = Mock()
    session.post.side_effect = [requests.exceptions.ReadTimeout(), _response({"features": [_item("A")], "links": []})]
    items, _, _ = stac.search({"collections": ["x"]}, max_items=None, session=session)
    assert [item["id"] for item in items] == ["A"]


def test_search_keeps_one_item_per_product_across_id_forms():
    session = Mock()
    session.post.return_value = _response({"features": [_item("S6A_X"), _item("S6A_X.SEN6")], "links": []})
    items, _, _ = stac.search({"collections": ["x"]}, max_items=None, session=session)
    assert [item["id"] for item in items] == ["S6A_X"]


def test_keep_check_does_not_count_towards_max_items():
    session = Mock()
    session.post.return_value = _response({"features": [_item("A"), _item("B")], "links": []})
    items, _, _ = stac.search({"collections": ["x"]}, max_items=1, session=session, keep=lambda item: item["id"] == "B")
    assert [item["id"] for item in items] == ["B"]


def test_item_starts_within_selects_by_sensing_start():
    check = stac.item_starts_within("2024-01-01T00:00:00", "2024-01-02T00:00:00Z")
    def item(start):
        return {"properties": {"start_datetime": start}}
    assert check(item("2024-01-01T00:00:00.000000Z"))
    assert check(item("2024-01-01T23:59:59.123456789Z"))
    assert not check(item("2023-12-31T23:59:59Z"))
    assert not check(item("2024-01-02T00:00:00Z"))
    assert check({"properties": {}})


@pytest.mark.parametrize(
    ("name", "needs_odata"),
    [
        (f"{PRODUCT}.SAFE", False),
        ("S1A_IW_GRDH_1SDV_20240101T003214_20240101T003238_051906_064571_1F54.SAFE", True),
        ("S1A_IW_GRDH_1SDV_20240101T003214_20240101T003238_051906_064571_1F54_COG.SAFE", False),
        ("S1A_IW_GRDH_1SDV_20240101T003214_20240101T003238_051906_064571_1F54_COG", False),
        ("S1A_IW_RAW__0SDV_20240101T003214", True),
        ("LC09_L1GT_001002_20240101", True),
        ("hello world", True),
        ("S2A_MSIL2A_20240613T100031_N0510", False),
        ("S5P_OFFL_L2__NO2____20240607T115910", False),
        ("Copernicus_DSM_COG_10_N42_00_E012_00_DEM", False),
    ],
)
def test_name_needs_odata(name, needs_odata):
    assert stac.name_needs_odata(name) is needs_odata


@patch("phidown.stac.list_collections", return_value=COLLECTIONS)
@patch("phidown.stac.requests.post")
def test_query_by_name_falls_back_to_odata_when_stac_is_empty(mock_post, _collections):
    mock_post.return_value = _response({"features": [], "links": []})
    with patch("phidown.search.requests.get", return_value=_odata_response([{"Id": "x"}])) as mock_get:
        df = CopernicusDataSearcher().query_by_name(PRODUCT)
    assert mock_post.call_count == 1
    assert f"Name eq '{PRODUCT}.SAFE'" in mock_get.call_args.args[0]
    assert list(df["Id"]) == ["x"]


@patch("phidown.stac.requests.post")
def test_query_by_name_of_non_cog_grd_uses_odata(mock_post):
    name = "S1A_IW_GRDH_1SDV_20240101T003214_20240101T003238_051906_064571_1F54.SAFE"
    with patch("phidown.search.requests.get", return_value=_odata_response([{"Id": "x"}])) as mock_get:
        CopernicusDataSearcher().query_by_name(name)
    mock_post.assert_not_called()
    assert f"Name eq '{name}'" in mock_get.call_args.args[0]


@pytest.mark.parametrize(
    ("match_type", "expected"),
    [
        ("exact", "Name eq 'a''b'"),
        ("contains", "contains(Name,'a''b')"),
        ("startswith", "startswith(Name,'a''b')"),
        ("endswith", "endswith(Name,'a''b')"),
    ],
)
@patch("phidown.stac.requests.post")
def test_name_pattern_search_uses_odata_and_escapes_quotes(mock_post, match_type, expected):
    with patch("phidown.search.requests.get", return_value=_odata_response([{"Id": "x"}])) as mock_get:
        df = CopernicusDataSearcher().search_products_by_name_pattern("a'b", match_type, top=5)
    mock_post.assert_not_called()
    assert expected in mock_get.call_args.args[0]
    assert list(df["Id"]) == ["x"]


def test_odata_filters_escape_values_and_encode_offsets():
    searcher = CopernicusDataSearcher()
    searcher.query_by_filter(
        burst_mode=True,
        parent_product_name="x' or 1 eq 1 or ParentProductName eq 'y",
        start_date="2024-08-02T00:00:00+02:00",
    )
    url = searcher._build_query()
    assert "ParentProductName eq 'x'' or 1 eq 1 or ParentProductName eq ''y'" in url
    assert "ContentDate/Start ge 2024-08-02T00:00:00%2B02:00" in url


def test_burst_parameters_require_burst_mode():
    with pytest.raises(ValueError, match="burst_id, swath_identifier"):
        CopernicusDataSearcher().query_by_filter(collection_name="SENTINEL-1", burst_id=1, swath_identifier="IW1")


@pytest.mark.parametrize(
    "query",
    [
        {"burst_mode": True, "order_by": "PublicationDate desc"},
        {"burst_mode": True, "order_by": "ModificationDate asc"},
        {"top": 2.5},
        {"start_date": "20240617"},
    ],
)
def test_invalid_parameters_are_rejected_when_set(query):
    with pytest.raises(ValueError):
        CopernicusDataSearcher().query_by_filter(collection_name="SENTINEL-1", **query)


def test_coverage_of_point_and_line_aois():
    pytest.importorskip("shapely")
    footprint = {"type": "Polygon", "coordinates": [[[0, 0], [2, 0], [2, 2], [0, 2], [0, 0]]]}
    searcher = CopernicusDataSearcher()
    searcher.aoi_wkt = "POINT(1 1)"
    assert searcher._calculate_aoi_coverage(footprint) == 100.0
    searcher.aoi_wkt = "POINT(5 5)"
    assert searcher._calculate_aoi_coverage(footprint) == 0.0
    searcher.aoi_wkt = "LINESTRING(1 1, 3 1)"
    assert searcher._calculate_aoi_coverage(footprint) == 50.0


def test_aoi_centroid_across_antimeridian():
    searcher = CopernicusDataSearcher()
    lon, _ = searcher._get_aoi_centroid("POLYGON((179 0, -179 0, -179 1, 179 1, 179 0))")
    assert abs(lon) == pytest.approx(180)


@patch("phidown.stac.list_collections", return_value=COLLECTIONS)
@patch("phidown.stac.requests.post")
def test_rejected_page_size_falls_back_to_odata(mock_post, _collections):
    mock_post.return_value = _response(
        {"detail": {"code": "LimitValidationError", "message": "Limit of 1000 exceeds maximum of 200."}},
        status_code=400,
    )
    with patch("phidown.search.requests.get", return_value=_odata_response([{"Id": "x"}])) as mock_get:
        searcher = CopernicusDataSearcher()
        searcher.query_by_filter(collection_name="SENTINEL-2", product_type="S2MSI2A")
        assert list(searcher.execute_query()["Id"]) == ["x"]
    assert mock_post.call_count == 1
    assert "$top=1000" in mock_get.call_args.args[0]


def test_landsat_8_uses_its_odata_collection_name():
    searcher = CopernicusDataSearcher()
    searcher.query_by_filter(collection_name="LANDSAT-8-ESA")
    assert "Collection/Name eq 'LANDSAT-8'" in searcher._build_query()


def test_cop_dem_product_types_select_collections():
    available = ["cop-dem-glo-30-dged-cog", "cop-dem-glo-90-dged-cog", "cop-dem-eea-10-laea-tif"]
    assert stac.resolve_collections("COP-DEM", "COP-DEM-GLO-30", available) == (["cop-dem-glo-30-dged-cog"], True)
    assert stac.resolve_collections("COP-DEM", "COP-DEM-GLO-90", available) == (["cop-dem-glo-90-dged-cog"], True)


@patch("phidown.stac.list_collections", return_value=["cop-dem-glo-30-dged-cog"])
@patch("phidown.stac.requests.post")
def test_cop_dem_name_pattern_uses_stac(mock_post, _collections):
    mock_post.return_value = _response({"features": [_item("Copernicus_DSM_COG_10_N42")], "links": []})
    df = CopernicusDataSearcher().search_products_by_name_pattern("DSM_COG", "contains", "COP-DEM", top=5)
    assert mock_post.call_args.kwargs["json"]["filter"]["args"][1] == "%DSM\\_COG%"
    assert len(df) == 1


def test_item_ids_and_odata_names_handle_extensions():
    assert stac.item_ids_for_name("S6A_X") == ["S6A_X", "S6A_X.SEN6"]
    assert stac.item_ids_for_name("S6A_X.SEN6") == ["S6A_X", "S6A_X.SEN6"]
    assert stac.item_ids_for_name("S5P_X.nc") == ["S5P_X", "S5P_X.nc"]
    assert stac.item_ids_for_name(f"{PRODUCT}.SAFE") == [PRODUCT]
    assert stac.odata_name_for_name("S1A_X") == "S1A_X.SAFE"
    assert stac.odata_name_for_name("S3A_X") == "S3A_X.SEN3"
    assert stac.odata_name_for_name("S6A_X") == "S6A_X.SEN6"
    assert stac.odata_name_for_name("S5P_X") == "S5P_X.nc"
    assert stac.odata_name_for_name("DEM1_X") == "DEM1_X.DEM"
    assert stac.odata_name_for_name("DEM1_X.DEM") == "DEM1_X.DEM"
    assert stac.item_id_for_name("DEM1_X.DEM") == "DEM1_X"
    assert stac.odata_name_for_name("S1A_X.SAFE") == "S1A_X.SAFE"
    assert stac.odata_name_for_name("LC08_X") == "LC08_X"


def test_odata_sends_integer_attributes_given_as_strings_as_integers():
    searcher = CopernicusDataSearcher()
    searcher.query_by_filter(collection_name="SENTINEL-1", product_type="SLC", attributes={"relativeOrbitNumber": "66"})
    url = searcher._build_query()
    assert "IntegerAttribute/Value eq 66" in url
    assert "StringAttribute/Value eq '66'" not in url


def test_odata_selects_sentinel3_groups_by_name():
    searcher = CopernicusDataSearcher()
    searcher.query_by_filter(collection_name="SENTINEL-3", product_type="S3OLCI", attributes={"instrumentShortName": "OLCI"})
    url = searcher._build_query()
    assert "contains(Name,'_OL_')" in url
    assert "Value eq 'S3OLCI'" not in url


@pytest.mark.parametrize("header", ["-5", "nan"])
def test_send_ignores_invalid_retry_after(header):
    session = Mock()
    session.get.side_effect = [_response({}, status_code=429, headers={"Retry-After": header}), _response({})]
    with patch("phidown.stac.time.sleep") as mock_sleep:
        stac._send(session, "GET", "https://stac")
    assert mock_sleep.call_args.args[0] == 1.0


@patch("phidown.stac.list_collections", return_value=COLLECTIONS)
@patch("phidown.stac.requests.post")
def test_query_by_name_resets_state_after_fallback(mock_post, _collections):
    mock_post.return_value = _response({"features": [], "links": []})
    searcher = CopernicusDataSearcher()
    with patch("phidown.search.requests.get", return_value=_odata_response([{"Id": "x"}])):
        searcher.query_by_name(PRODUCT)
    assert searcher.query is None
    assert searcher.num_results == 1


@patch("phidown.stac.requests.post")
def test_download_product_reports_product_without_s3_path(mock_post, capsys):
    with patch("phidown.search.requests.get", return_value=_odata_response([{"Id": "x", "Name": "ENV_X", "ContentLength": 0}])):
        assert CopernicusDataSearcher().download_product("ENV_X", "/tmp/unused") is False
    assert "no S3 path" in capsys.readouterr().out
