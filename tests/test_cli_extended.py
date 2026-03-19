"""Extended tests for CLI helpers, list mode, and burst coverage mode."""

import json
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from phidown.cli import (
    _parse_bbox_to_wkt,
    _parse_columns,
    burst_coverage_analysis,
    list_products,
    main,
)


class TestCliHelpers:
    """Unit tests for helper parsing functions."""

    def test_parse_bbox_to_wkt_from_sequence(self):
        wkt = _parse_bbox_to_wkt([-5, 40, 5, 45])
        assert wkt == "POLYGON((-5.0 40.0, 5.0 40.0, 5.0 45.0, -5.0 45.0, -5.0 40.0))"

    def test_parse_bbox_to_wkt_from_csv_string(self):
        wkt = _parse_bbox_to_wkt("-5,40,5,45")
        assert wkt == "POLYGON((-5.0 40.0, 5.0 40.0, 5.0 45.0, -5.0 45.0, -5.0 40.0))"

    def test_parse_bbox_to_wkt_rejects_bad_shape(self):
        with pytest.raises(ValueError, match="exactly 4"):
            _parse_bbox_to_wkt("-5,40,5")

    def test_parse_bbox_to_wkt_rejects_bad_bounds(self):
        with pytest.raises(ValueError, match="min_lon < max_lon"):
            _parse_bbox_to_wkt([5, 40, -5, 45])

    def test_parse_bbox_to_wkt_rejects_non_numeric(self):
        with pytest.raises(ValueError, match="numeric"):
            _parse_bbox_to_wkt("-5,forty,5,45")

    def test_parse_columns_none(self):
        assert _parse_columns(None) is None

    def test_parse_columns_trim(self):
        assert _parse_columns(" Name , S3Path ,ContentDate ") == ["Name", "S3Path", "ContentDate"]

    def test_parse_columns_rejects_empty(self):
        with pytest.raises(ValueError, match="at least one column"):
            _parse_columns(" , ")


class TestListProductsExtended:
    """Extended tests for list_products behavior."""

    @patch("phidown.cli.CopernicusDataSearcher")
    def test_list_products_empty_results_returns_true(self, mock_searcher_class):
        mock_searcher = MagicMock()
        mock_searcher_class.return_value = mock_searcher
        mock_searcher.execute_query.return_value = pd.DataFrame()

        assert list_products(
            collection="SENTINEL-1",
            bbox=[-5, 40, 5, 45],
            start_date="2024-01-01T00:00:00",
        )

    @patch("phidown.cli.CopernicusDataSearcher")
    def test_list_products_missing_requested_columns_returns_false(self, mock_searcher_class):
        mock_searcher = MagicMock()
        mock_searcher_class.return_value = mock_searcher
        mock_searcher.execute_query.return_value = pd.DataFrame({"Name": ["A"]})

        assert not list_products(
            collection="SENTINEL-1",
            bbox=[-5, 40, 5, 45],
            start_date="2024-01-01T00:00:00",
            columns="Name,S3Path",
        )

    @patch("phidown.cli.CopernicusDataSearcher")
    def test_list_products_save_json(self, mock_searcher_class, tmp_path):
        mock_searcher = MagicMock()
        mock_searcher_class.return_value = mock_searcher
        mock_searcher.execute_query.return_value = pd.DataFrame(
            {"Name": ["A"], "S3Path": ["/eodata/path"], "ContentDate": ["2024-01-01T00:00:00Z"]}
        )

        target = tmp_path / "products.json"
        ok = list_products(
            collection="SENTINEL-1",
            bbox=[-5, 40, 5, 45],
            start_date="2024-01-01T00:00:00",
            output_format="json",
            save_path=str(target),
        )
        assert ok
        payload = json.loads(target.read_text(encoding="utf-8"))
        assert payload[0]["Name"] == "A"

    @patch("phidown.cli.CopernicusDataSearcher")
    def test_list_products_passes_bbox_over_aoi(self, mock_searcher_class):
        mock_searcher = MagicMock()
        mock_searcher_class.return_value = mock_searcher
        mock_searcher.execute_query.return_value = pd.DataFrame({"Name": ["A"]})

        list_products(
            collection="SENTINEL-1",
            aoi_wkt="POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))",
            bbox=[-5, 40, 5, 45],
            start_date="2024-01-01T00:00:00",
        )
        assert mock_searcher.query_by_filter.call_args.kwargs["aoi_wkt"].startswith("POLYGON((-5.0 40.0")

    @patch("phidown.cli.CopernicusDataSearcher")
    def test_list_products_handles_search_exceptions(self, mock_searcher_class):
        mock_searcher = MagicMock()
        mock_searcher_class.return_value = mock_searcher
        mock_searcher.query_by_filter.side_effect = RuntimeError("boom")

        assert not list_products(
            collection="SENTINEL-1",
            bbox=[-5, 40, 5, 45],
            start_date="2024-01-01T00:00:00",
        )


class TestBurstCoverageExtended:
    """Extended tests for burst_coverage_analysis behavior."""

    @patch("phidown.cli.CopernicusDataSearcher")
    def test_burst_coverage_empty_results_returns_true(self, mock_searcher_class):
        mock_searcher = MagicMock()
        mock_searcher_class.return_value = mock_searcher
        mock_searcher.find_optimal_bursts.return_value = pd.DataFrame()

        assert burst_coverage_analysis(
            bbox=[-5, 40, 5, 45],
            start_date="2024-08-02T00:00:00",
            end_date="2024-08-15T23:59:59",
        )

    @patch("phidown.cli.CopernicusDataSearcher")
    def test_burst_coverage_missing_requested_columns_returns_false(self, mock_searcher_class):
        mock_searcher = MagicMock()
        mock_searcher_class.return_value = mock_searcher
        mock_searcher.find_optimal_bursts.return_value = pd.DataFrame({"BurstId": [1]})

        assert not burst_coverage_analysis(
            bbox=[-5, 40, 5, 45],
            start_date="2024-08-02T00:00:00",
            end_date="2024-08-15T23:59:59",
            columns="BurstId,S3Path",
        )

    @patch("phidown.cli.CopernicusDataSearcher")
    def test_burst_coverage_preferred_subswath_parsing(self, mock_searcher_class):
        mock_searcher = MagicMock()
        mock_searcher_class.return_value = mock_searcher
        mock_searcher.find_optimal_bursts.return_value = pd.DataFrame({"BurstId": [1]})

        burst_coverage_analysis(
            bbox=[-5, 40, 5, 45],
            start_date="2024-08-02T00:00:00",
            end_date="2024-08-15T23:59:59",
            preferred_subswath="iw3, IW1,iw2",
        )
        assert mock_searcher.find_optimal_bursts.call_args.kwargs["preferred_subswath"] == ["IW3", "IW1", "IW2"]

    @patch("phidown.cli.CopernicusDataSearcher")
    def test_burst_coverage_summary_in_table_output(self, mock_searcher_class, capsys):
        mock_searcher = MagicMock()
        mock_searcher_class.return_value = mock_searcher
        mock_searcher.find_optimal_bursts.return_value = pd.DataFrame(
            {"BurstId": [1, 2], "SwathIdentifier": ["IW1", "IW2"], "coverage": [60.0, 80.0]}
        )

        assert burst_coverage_analysis(
            bbox=[-5, 40, 5, 45],
            start_date="2024-08-02T00:00:00",
            end_date="2024-08-15T23:59:59",
            output_format="table",
        )
        out = capsys.readouterr().out
        assert "total_bursts=2" in out
        assert "mean_coverage=70.0" in out

    @patch("phidown.cli.CopernicusDataSearcher")
    def test_burst_coverage_save_json_contains_summary(self, mock_searcher_class, tmp_path):
        mock_searcher = MagicMock()
        mock_searcher_class.return_value = mock_searcher
        mock_searcher.find_optimal_bursts.return_value = pd.DataFrame(
            {"BurstId": [1], "SwathIdentifier": ["IW1"], "coverage": [90.0]}
        )

        target = tmp_path / "burst.json"
        ok = burst_coverage_analysis(
            bbox=[-5, 40, 5, 45],
            start_date="2024-08-02T00:00:00",
            end_date="2024-08-15T23:59:59",
            output_format="json",
            save_path=str(target),
        )
        assert ok
        payload = json.loads(target.read_text(encoding="utf-8"))
        assert payload["summary"]["total_bursts"] == 1
        assert payload["summary"]["max_coverage"] == 90.0

    @patch("phidown.cli.CopernicusDataSearcher")
    def test_burst_coverage_handles_search_exceptions(self, mock_searcher_class):
        mock_searcher = MagicMock()
        mock_searcher_class.return_value = mock_searcher
        mock_searcher.find_optimal_bursts.side_effect = RuntimeError("boom")

        assert not burst_coverage_analysis(
            bbox=[-5, 40, 5, 45],
            start_date="2024-08-02T00:00:00",
            end_date="2024-08-15T23:59:59",
        )


class TestMainCliExtended:
    """Additional main() argument-validation tests."""

    @patch("sys.argv", ["phidown", "--list", "--aoi-wkt", "POLYGON((0 0,1 0,1 1,0 1,0 0))"])
    def test_list_requires_temporal_filter(self):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code != 0

    @patch(
        "sys.argv",
        [
            "phidown",
            "--list",
            "--aoi-wkt",
            "POLYGON((0 0,1 0,1 1,0 1,0 0))",
            "--bbox",
            "-5",
            "40",
            "5",
            "45",
            "--start-date",
            "2024-01-01T00:00:00",
        ],
    )
    def test_list_rejects_multiple_spatial_filters(self):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code != 0

    @patch("sys.argv", ["phidown", "--burst-coverage", "--start-date", "2024-08-02T00:00:00", "--end-date", "2024-08-15T23:59:59"])
    def test_burst_coverage_requires_spatial_filter(self):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code != 0

    @patch(
        "sys.argv",
        [
            "phidown",
            "--burst-coverage",
            "--aoi-wkt",
            "POLYGON((0 0,1 0,1 1,0 1,0 0))",
            "--bbox",
            "-5",
            "40",
            "5",
            "45",
            "--start-date",
            "2024-08-02T00:00:00",
            "--end-date",
            "2024-08-15T23:59:59",
        ],
    )
    def test_burst_coverage_rejects_multiple_spatial_filters(self):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code != 0

    @patch("phidown.cli.list_products", side_effect=KeyboardInterrupt)
    @patch(
        "sys.argv",
        [
            "phidown",
            "--list",
            "--bbox",
            "-5",
            "40",
            "5",
            "45",
            "--start-date",
            "2024-01-01T00:00:00",
        ],
    )
    def test_keyboard_interrupt_returns_130(self, _mock_list):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 130
