"""Unit tests for the STAC product search.

The STAC responses below are fixed fixtures shaped like CDSE STAC items.
They do not replace a live check against https://stac.dataspace.copernicus.eu.
"""

from unittest.mock import Mock, patch

import pytest

from phidown import stac
from phidown.search import CopernicusDataSearcher

# Real collection ids from https://stac.dataspace.copernicus.eu/v1/collections (subset).
COLLECTIONS = [
    "sentinel-1-etad", "sentinel-1-global-mosaics", "sentinel-1-grd", "sentinel-1-ocn", "sentinel-1-slc",
    "sentinel-1-slc-burst", "sentinel-1-slc-wv", "sentinel-2-global-mosaics", "sentinel-2-gri-l1c",
    "sentinel-2-l1c", "sentinel-2-l2a", "sentinel-2-l2a-tlm", "sentinel-3-olci-2-lfr-nrt",
    "sentinel-3-olci-2-lfr-ntc", "sentinel-3-sr-1-sra-a-ntc", "sentinel-3-sr-1-sra-ntc",
    "sentinel-5p-l2-no2", "sentinel-5p-l2-no2-offl", "sentinel-5p-l2-no2-nrti",
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
    assert stac.resolve_collections("SENTINEL-1", "SLC", COLLECTIONS) == (["sentinel-1-slc"], True)
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
    assert stac.resolve_collections("SENTINEL-5P", "L2__NO2___", COLLECTIONS) == (["sentinel-5p-l2-no2"], True)
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


def test_collections_for_product_name():
    assert stac.collections_for_product_name(PRODUCT, COLLECTIONS) == ["sentinel-1-slc"]
    assert stac.collections_for_product_name("S1A_IW_GRDH_1SDV_20240610T170608_X.SAFE", COLLECTIONS) == ["sentinel-1-grd"]
    assert stac.collections_for_product_name("S2A_MSIL2A_20240613T100031_N0510", COLLECTIONS) == ["sentinel-2-l2a"]
    assert stac.collections_for_product_name(
        "S3B_OL_2_LFR____20240612T092654_20240612T092954_20250720T172843_0179_094_093_2160_ESA_R_NT_003.SEN3", COLLECTIONS
    ) == ["sentinel-3-olci-2-lfr-ntc"]
    assert stac.collections_for_product_name("S1", COLLECTIONS) == S1_DEFAULT
    assert "sentinel-1-slc-burst" not in stac.collections_for_product_name("", COLLECTIONS)


def test_datetime_window_for_name():
    assert stac.datetime_window_for_name(PRODUCT) == "2024-01-01T00:00:00Z/2024-01-04T00:00:00Z"
    assert stac.datetime_window_for_name("S2B_MSIL2A_20240608T0955") == "2024-06-07T00:00:00Z/2024-06-10T00:00:00Z"
    assert stac.datetime_window_for_name("IW_SLC") is None
    assert stac.datetime_window_for_name("_20241399") is None


def test_item_ids_for_name_handles_extension_and_cog_suffix():
    assert stac.item_ids_for_name(f"{PRODUCT}.SAFE", ["sentinel-1-slc"]) == [PRODUCT]
    assert stac.item_ids_for_name(PRODUCT, ["sentinel-1-slc"]) == [PRODUCT]
    assert stac.item_ids_for_name("S1A_IW_GRDH_X.SAFE", ["sentinel-1-grd"]) == ["S1A_IW_GRDH_X_COG"]
    assert stac.item_ids_for_name("S1A_IW_GRDH_X_COG.SAFE", ["sentinel-1-grd"]) == ["S1A_IW_GRDH_X_COG"]


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
            {"op": "a_contains", "args": [{"property": "sar:polarizations"}, ["VV"]]},
            {"op": "a_contains", "args": [{"property": "sar:polarizations"}, ["VH"]]},
            {"op": "=", "args": [{"property": "platform"}, "sentinel-2a"]},
            {"op": "=", "args": [{"property": "grid:code"}, "MGRS-33TUG"]},
        ],
    }


def test_build_search_body_open_date_range_and_no_filter():
    body = stac.build_search_body(collections=["x"], start_date="2024-01-01T00:00:00Z")
    assert body["datetime"] == "2024-01-01T00:00:00Z/.."
    body = stac.build_search_body(collections=["x"], start_date="2024-01-01T00:00:00", end_date="2024-02-01")
    assert body["datetime"] == "2024-01-01T00:00:00Z/2024-02-01T00:00:00Z"
    assert stac.build_search_body(collections=["x"], end_date="2024-02-01T00:00:00+01:00")["datetime"] == "../2024-02-01T00:00:00+01:00"
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
    assert record["Footprint"].startswith("POLYGON ((10 40")
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


def test_search_moves_rejected_filter_properties_to_client():
    rejected = _response({"detail": {
        "code": "FilterValidationError",
        "collections": {"sentinel-1-ocn": {"invalid_attributes": ["sat:orbit_state"]}},
    }}, status_code=400)
    ascending = _item("A")
    ascending["properties"]["sat:orbit_state"] = "ascending"
    page = _response({"features": [ascending, _item("B")], "links": []})
    session = Mock()
    session.post.side_effect = [rejected, page]
    body = {"collections": ["sentinel-1-ocn"], "filter-lang": "cql2-json", "filter": {"op": "and", "args": [
        {"op": "=", "args": [{"property": "sat:orbit_state"}, "descending"]},
        {"op": "like", "args": [{"property": "id"}, "B%"]},
    ]}}

    items, _, _ = stac.search(body, max_items=None, session=session)

    assert [item["id"] for item in items] == ["B"]
    assert session.post.call_args_list[1].kwargs["json"]["filter"] == {"op": "like", "args": [{"property": "id"}, "B%"]}


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
    assert body["collections"] == ["sentinel-1-slc"]
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


@patch("phidown.stac.list_collections", return_value=COLLECTIONS)
@patch("phidown.stac.requests.post")
def test_name_pattern_search_uses_like_filter(mock_post, _collections):
    mock_post.return_value = _response({"features": [_item()], "links": []})
    searcher = CopernicusDataSearcher()

    df = searcher.search_products_by_name_pattern("IW_SLC", "contains", collection_name_filter="SENTINEL-1", top=5)

    body = mock_post.call_args.kwargs["json"]
    assert body["filter"] == {"op": "like", "args": [{"property": "id"}, "%IW\\_SLC%"]}
    assert body["collections"] == S1_DEFAULT
    assert len(df) == 1


def test_list_collections_follows_next_links_and_caches():
    first = _response({"collections": [{"id": "a"}], "links": [{"rel": "next", "href": "https://stac/collections?offset=1"}]})
    second = _response({"collections": [{"id": "b"}], "links": []})
    with patch("phidown.stac.requests.get", side_effect=[first, second]) as mock_get:
        assert stac.list_collections("https://stac") == ["a", "b"]
        assert stac.list_collections("https://stac") == ["a", "b"]
    assert mock_get.call_count == 2


@patch("phidown.stac.list_collections", return_value=COLLECTIONS)
@patch("phidown.stac.requests.post")
def test_exact_name_pattern_drops_extension_and_adds_date_window(mock_post, _collections):
    mock_post.return_value = _response({"features": [_item()], "links": []})
    searcher = CopernicusDataSearcher()

    df = searcher.search_products_by_name_pattern(f"{PRODUCT}.SAFE", "exact", top=5)

    body = mock_post.call_args.kwargs["json"]
    assert body["collections"] == ["sentinel-1-slc"]
    assert body["filter"]["args"][1] == PRODUCT.replace("_", "\\_")
    assert body["datetime"] == "2024-01-01T00:00:00Z/2024-01-04T00:00:00Z"
    assert list(df["Name"]) == [f"{PRODUCT}.SAFE"]
