"""Tests for the PhiSat-2 provider helpers."""

from __future__ import annotations

from unittest.mock import patch

import pandas as pd
import requests

from phidown.search import CopernicusDataSearcher
from phidown.phisat2 import (
    DEFAULT_API_BASE,
    PHISAT2_SECTION,
    PhiSat2Config,
    PhiSat2Searcher,
    ensure_phisat2_config,
)


class FakeResponse:
    def __init__(self, *, payload=None, headers=None, chunks=None, status_code=200):
        self._payload = payload or {}
        self.headers = headers or {}
        self._chunks = chunks or []
        self.status_code = status_code

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"status {self.status_code}")

    def iter_content(self, chunk_size=1024):
        del chunk_size
        for chunk in self._chunks:
            yield chunk


def _phisat2_config() -> PhiSat2Config:
    return PhiSat2Config(username="user@example.com", password="secret")


@patch("phidown.phisat2.requests.get")
@patch("phidown.phisat2._build_headers", return_value={"Authorization": "Bearer test"})
@patch("phidown.phisat2._read_phisat2_config")
@patch("phidown.phisat2.ensure_phisat2_config")
def test_common_search_api_routes_phisat2_collection(
    mock_ensure,
    mock_read_config,
    mock_headers,
    mock_get,
):
    del mock_ensure, mock_headers
    mock_read_config.return_value = _phisat2_config()
    mock_get.return_value = FakeResponse(
        payload={
            "page": {"totalElements": 1},
            "features": [
                {
                    "id": "feature-1",
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[-3.8, 40.4], [-3.6, 40.4], [-3.6, 40.6], [-3.8, 40.6], [-3.8, 40.4]]],
                    },
                    "properties": {
                        "filename": "PHISAT-2_L1_PRODUCT.zip",
                        "filesize": 1234,
                        "startDate": "2026-05-14T11:21:45Z",
                        "completionDate": "2026-05-14T11:21:48Z",
                        "published": "2026-05-14T17:12:13Z",
                        "_links": {
                            "download": {
                                "href": "https://phisat2.insula.earth/secure/api/v2.0/search/dl/platform/42"
                            }
                        },
                    }
                }
            ],
        }
    )

    searcher = CopernicusDataSearcher()
    searcher.query_by_filter(
        collection_name="PHISAT-2",
        product_type="L1",
        aoi_wkt="POLYGON((-3.9 40.3, -3.5 40.3, -3.5 40.7, -3.9 40.7, -3.9 40.3))",
        start_date="2026-05-01T00:00:00Z",
        end_date="2026-05-30T23:59:59Z",
        top=5,
        config_file="dummy.s5cfg",
    )
    df = searcher.execute_query()

    assert searcher.collection_name == "PHISAT-2"
    assert df.loc[0, "Provider"] == "phisat2"
    assert df.loc[0, "Name"] == "PHISAT-2_L1_PRODUCT.zip"
    assert df.loc[0, "ContentLength"] == 1234
    assert df.loc[0, "ContentDate"] == {
        "Start": "2026-05-14T11:21:45Z",
        "End": "2026-05-14T11:21:48Z",
    }
    assert df.loc[0, "GeoFootprint"]["type"] == "Polygon"
    assert df.loc[0, "DownloadUrl"].endswith("/search/dl/platform/42")
    assert mock_get.call_args.kwargs["params"] == {
        "catalogue": "REF_DATA",
        "refDataCollection": "phisat24e55ba83dd304ea9b018b65e9b17a7de",
        "identifier": "L1",
        "resultsPerPage": 5,
        "page": 0,
        "aoi": "POLYGON((-3.9 40.3, -3.5 40.3, -3.5 40.7, -3.9 40.7, -3.9 40.3))",
        "productDateStart": "2026-05-01T00:00:00Z",
        "productDateEnd": "2026-05-30T23:59:59Z",
    }


@patch("phidown.phisat2.requests.get")
@patch("phidown.phisat2._build_headers", return_value={"Authorization": "Bearer test"})
@patch("phidown.phisat2._read_phisat2_config")
@patch("phidown.phisat2.ensure_phisat2_config")
def test_common_search_api_defaults_phisat2_product_type(
    mock_ensure,
    mock_read_config,
    mock_headers,
    mock_get,
):
    del mock_ensure, mock_headers
    mock_read_config.return_value = _phisat2_config()
    mock_get.return_value = FakeResponse(payload={"features": []})

    searcher = CopernicusDataSearcher()
    searcher.query_by_filter(collection_name="PHISAT-2", top=5, config_file="dummy.s5cfg")
    searcher.execute_query()

    assert searcher.product_type == "L1"
    assert mock_get.call_args.kwargs["params"]["identifier"] == "L1"


@patch("phidown.phisat2.requests.get")
@patch("phidown.phisat2._build_headers", return_value={"Authorization": "Bearer test"})
@patch("phidown.phisat2._read_phisat2_config")
@patch("phidown.phisat2.ensure_phisat2_config")
def test_common_search_api_keeps_phisat2_filter_text_compatibility(
    mock_ensure,
    mock_read_config,
    mock_headers,
    mock_get,
):
    del mock_ensure, mock_headers
    mock_read_config.return_value = _phisat2_config()
    mock_get.return_value = FakeResponse(
        payload={
            "_embedded": {
                "platformFiles": [
                    {
                        "id": 42,
                        "filename": "PRODUCT_A.zip",
                        "contentLength": 1234,
                        "createdAt": "2026-04-20T10:00:00Z",
                    }
                ]
            }
        }
    )

    searcher = CopernicusDataSearcher()
    searcher.query_by_filter(collection_name="PHISAT-2", filter_text="SESSION_ID_12345", top=5)
    df = searcher.execute_query()

    assert df.loc[0, "Name"] == "PRODUCT_A.zip"
    assert mock_get.call_args.kwargs["params"] == {
        "filter": "SESSION_ID_12345",
        "resultsPerPage": 5,
    }


@patch("phidown.search.PhiSat2Searcher")
def test_common_download_api_routes_phisat2_collection(mock_searcher_class, tmp_path):
    mock_searcher = mock_searcher_class.return_value
    target = tmp_path / "PRODUCT_A.zip"
    mock_searcher.download_url.return_value = str(target)

    searcher = CopernicusDataSearcher()
    searcher.query_by_filter(collection_name="PHISAT-2", product_type="L1", top=1)
    searcher.df = pd.DataFrame(
        {
            "Name": ["PRODUCT_A.zip"],
            "DownloadUrl": ["https://phisat2.insula.earth/secure/api/v2.0/search/dl/platform/42"],
        }
    )

    result = searcher.download_product(
        "PRODUCT_A.zip",
        output_dir=str(tmp_path),
        config_file="dummy.s5cfg",
        show_progress=False,
        verbose=False,
    )

    assert result is True
    assert searcher.last_download_path == str(target)
    mock_searcher.download_url.assert_called_once()


def test_ensure_phisat2_config_preserves_default_section(tmp_path):
    cfg = tmp_path / ".s5cfg"
    cfg.write_text(
        "\n".join(
            [
                "[default]",
                "aws_access_key_id = keep-access",
                "aws_secret_access_key = keep-secret",
            ]
        ),
        encoding="utf-8",
    )

    with patch("builtins.input", return_value="phisat@example.com"), patch(
        "getpass.getpass", return_value="phisat-password"
    ):
        ensure_phisat2_config(str(cfg), reset=False)

    content = cfg.read_text(encoding="utf-8")
    assert "[default]" in content
    assert "aws_access_key_id = keep-access" in content
    assert f"[{PHISAT2_SECTION}]" in content
    assert "username = phisat@example.com" in content
    assert "password = phisat-password" in content


@patch("phidown.phisat2.requests.get")
@patch("phidown.phisat2._build_headers", return_value={"Authorization": "Bearer test"})
@patch("phidown.phisat2._read_phisat2_config")
@patch("phidown.phisat2.ensure_phisat2_config")
def test_query_normalizes_platform_file_response(
    mock_ensure,
    mock_read_config,
    mock_headers,
    mock_get,
):
    del mock_ensure, mock_headers
    mock_read_config.return_value = _phisat2_config()
    mock_get.return_value = FakeResponse(
        payload={
            "_embedded": {
                "platformFiles": [
                    {
                        "id": 42,
                        "filename": "PRODUCT_A.zip",
                        "contentLength": 1234,
                        "createdAt": "2026-04-20T10:00:00Z",
                    }
                ]
            }
        }
    )

    searcher = PhiSat2Searcher(config_file="dummy.s5cfg")
    df = searcher.query("SESSION_ID_12345", results_per_page=5)

    assert df.loc[0, "Id"] == 42
    assert df.loc[0, "Name"] == "PRODUCT_A.zip"
    assert df.loc[0, "ContentLength"] == 1234
    assert df.loc[0, "DownloadUrl"] == f"{DEFAULT_API_BASE}/platformFiles/42/dl"
    assert df.loc[0, "Provider"] == "phisat2"
    assert mock_get.call_args.kwargs["params"] == {"filter": "SESSION_ID_12345", "resultsPerPage": 5}


def test_resolve_product_prefers_exact_filename():
    searcher = PhiSat2Searcher(config_file="dummy.s5cfg")
    with patch.object(
        searcher,
        "query",
        return_value=pd.DataFrame(
            {
                "Id": [1, 2],
                "Name": ["PRODUCT_A.zip", "PRODUCT_A"],
            }
        ),
    ):
        resolved = searcher.resolve_product("PRODUCT_A.zip")

    assert resolved["Id"] == 1


def test_resolve_product_accepts_platform_file_basename():
    searcher = PhiSat2Searcher(config_file="dummy.s5cfg")
    with patch.object(
        searcher,
        "query",
        return_value=pd.DataFrame(
            {
                "Id": [1],
                "Name": ["8/PRODUCT_A.zip"],
            }
        ),
    ):
        resolved = searcher.resolve_product("PRODUCT_A.zip")

    assert resolved["Id"] == 1


def test_resolve_product_rejects_ambiguous_matches():
    searcher = PhiSat2Searcher(config_file="dummy.s5cfg")
    with patch.object(
        searcher,
        "query",
        return_value=pd.DataFrame(
            {
                "Id": [1, 2],
                "Name": ["PRODUCT_A_v1.zip", "PRODUCT_A_v2.zip"],
            }
        ),
    ):
        try:
            searcher.resolve_product("PRODUCT_A")
        except ValueError as exc:
            message = str(exc)
        else:  # pragma: no cover
            raise AssertionError("Expected ValueError for ambiguous PhiSat-2 matches")

    assert "Multiple PhiSat-2 products matched PRODUCT_A" in message


@patch("phidown.phisat2.requests.get")
@patch("phidown.phisat2._build_headers", return_value={"Authorization": "Bearer test"})
@patch("phidown.phisat2._read_phisat2_config")
@patch("phidown.phisat2.ensure_phisat2_config")
def test_download_product_writes_target_file(
    mock_ensure,
    mock_read_config,
    mock_headers,
    mock_get,
    tmp_path,
):
    del mock_ensure, mock_headers
    mock_read_config.return_value = _phisat2_config()
    mock_get.return_value = FakeResponse(
        headers={
            "content-disposition": 'attachment; filename="PRODUCT_A.zip"',
            "content-length": "11",
        },
        chunks=[b"hello ", b"world"],
    )

    searcher = PhiSat2Searcher(config_file="dummy.s5cfg")
    output_path = searcher.download_product(
        product_id=42,
        output_dir=str(tmp_path),
        show_progress=False,
    )

    assert output_path.endswith("PRODUCT_A.zip")
    assert (tmp_path / "PRODUCT_A.zip").read_bytes() == b"hello world"
    assert mock_get.call_args.kwargs["timeout"] == (30.0, 900.0)


def test_query_by_name_returns_unique_fuzzy_match():
    searcher = PhiSat2Searcher(config_file="dummy.s5cfg")
    with patch.object(
        searcher,
        "query",
        return_value=pd.DataFrame(
            {
                "Id": [7],
                "Name": ["SESSION123_product.zip"],
            }
        ),
    ):
        df = searcher.query_by_name("SESSION123")

    assert len(df) == 1
    assert df.iloc[0]["Id"] == 7
