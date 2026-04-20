"""Tests for the PhiSat-2 provider helpers."""

from __future__ import annotations

from unittest.mock import patch

import pandas as pd
import requests

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
