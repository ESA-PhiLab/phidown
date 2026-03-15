"""Tests for CopernicusDataSearcher.download_product retry behavior."""

from unittest.mock import MagicMock, patch

import pandas as pd

from phidown.search import CopernicusDataSearcher


class TestDownloadProduct:
    """Retry-focused tests for single-product downloads."""

    @patch("phidown.search.time.sleep", return_value=None)
    @patch("phidown.search.download_s3_resumable")
    def test_safe_mode_retries_until_success(self, mock_native, mock_sleep):
        searcher = CopernicusDataSearcher()
        searcher.query_by_name = MagicMock(return_value=pd.DataFrame(
            {"S3Path": ["/eodata/Sentinel-1/SAR/test.SAFE"], "ContentLength": [1024]}
        ))

        mock_native.side_effect = [
            RuntimeError("transient"),
            MagicMock(status="downloaded"),
        ]

        result = searcher.download_product(
            "TEST_PRODUCT",
            output_dir=".",
            mode="safe",
            retry_count=3,
            show_progress=False,
            verbose=False,
            reset_config=True,
        )

        assert result is True
        assert mock_native.call_count == 2
        assert mock_native.call_args_list[0].kwargs["attempts"] == 1
        assert mock_native.call_args_list[1].kwargs["attempts"] == 2
        assert mock_native.call_args_list[0].kwargs["reset_config"] is True
        assert mock_native.call_args_list[1].kwargs["reset_config"] is False
        mock_sleep.assert_called_once()

    @patch("phidown.search.time.sleep", return_value=None)
    @patch("phidown.search.download_s3_resumable", side_effect=RuntimeError("boom"))
    def test_safe_mode_returns_false_after_retry_exhaustion(self, mock_native, mock_sleep):
        searcher = CopernicusDataSearcher()
        searcher.query_by_name = MagicMock(return_value=pd.DataFrame(
            {"S3Path": ["/eodata/Sentinel-1/SAR/test.SAFE"], "ContentLength": [1024]}
        ))

        result = searcher.download_product(
            "TEST_PRODUCT",
            output_dir=".",
            mode="safe",
            retry_count=3,
            show_progress=False,
            verbose=False,
        )

        assert result is False
        assert mock_native.call_count == 3
        assert [call.kwargs["attempts"] for call in mock_native.call_args_list] == [1, 2, 3]
        assert mock_sleep.call_count == 2
