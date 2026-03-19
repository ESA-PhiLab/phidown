from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from phidown.insar_workflow import (
    _platform_filter,
    _save_coverage_plot,
    BurstSearchConfig,
    build_burst_workflow_config,
    compute_burst_statistics,
    debug_burst_summary,
    find_orbit_configuration,
    run_burst_workflow,
    save_workflow_outputs,
    search_bursts,
    validate_burst_results,
)


def test_build_burst_workflow_config_defaults():
    cfg = build_burst_workflow_config(
        {
            "search": {
                "aoi_wkt": "POLYGON((12.4 41.8, 12.6 41.8, 12.6 42.0, 12.4 42.0, 12.4 41.8))",
                "start_date": "2025-01-01T00:00:00",
                "end_date": "2025-03-01T00:00:00",
            }
        }
    )
    assert cfg.search.polarisation == "VV"
    assert cfg.search.max_results == 1000
    assert cfg.search.platforms == ["ALL"]


def test_build_burst_workflow_config_rejects_invalid_sections():
    with pytest.raises(TypeError, match="dictionary"):
        build_burst_workflow_config([])

    with pytest.raises(TypeError, match="search"):
        build_burst_workflow_config({"search": []})


def test_platform_filter_behaviour():
    assert _platform_filter([]) is None
    assert _platform_filter(["all"]) is None
    assert _platform_filter(["a"]) == "A"
    assert _platform_filter(["A", "B"]) is None


def test_find_orbit_configuration_uses_recommendation_when_missing_explicit_values():
    cfg = BurstSearchConfig(
        aoi_wkt="POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))",
        start_date="2025-01-01T00:00:00",
        end_date="2025-01-10T00:00:00",
    )
    searcher = MagicMock()
    searcher.find_optimal_orbit.return_value = {
        "recommended": {"orbit_direction": "DESCENDING", "relative_orbit": 66}
    }

    orbit = find_orbit_configuration(cfg, searcher=searcher)

    assert orbit["orbit_direction"] == "DESCENDING"
    assert orbit["relative_orbit"] == 66


def test_search_bursts_filters_platforms_and_sorts_by_priority():
    cfg = BurstSearchConfig(
        aoi_wkt="POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))",
        start_date="2025-01-01T00:00:00",
        end_date="2025-01-10T00:00:00",
        platforms=["A", "B"],
    )
    searcher = MagicMock()
    searcher.find_optimal_orbit.return_value = {
        "recommended": {"orbit_direction": "DESCENDING", "relative_orbit": 66}
    }
    searcher.execute_query.return_value = pd.DataFrame(
        [
            {"Id": "1", "PlatformSerialIdentifier": "A", "SwathIdentifier": "IW2", "coverage": 50.0},
            {"Id": "2", "PlatformSerialIdentifier": "B", "SwathIdentifier": "IW1", "coverage": 50.0},
            {"Id": "3", "PlatformSerialIdentifier": "C", "SwathIdentifier": "IW1", "coverage": 90.0},
            {"Id": "4", "PlatformSerialIdentifier": "A", "SwathIdentifier": "IW3", "coverage": 10.0},
        ]
    )

    result = search_bursts(cfg, searcher=searcher)

    assert result["Id"].tolist() == ["2", "1", "4"]
    assert searcher.query_by_filter.call_args.kwargs["count"] is True
    assert searcher.query_by_filter.call_args.kwargs["platform_serial_identifier"] is None


def test_compute_burst_statistics_empty_short_circuit():
    searcher = MagicMock()

    assert compute_burst_statistics(pd.DataFrame(), searcher=searcher) == {}
    searcher.compute_temporal_statistics.assert_not_called()


def test_validate_burst_results_ok():
    df = pd.DataFrame(
        [
            {
                "Id": "abc",
                "GeoFootprint": {"type": "Polygon", "coordinates": [[[12.4, 41.8], [12.6, 41.8], [12.6, 42.0], [12.4, 42.0], [12.4, 41.8]]]},
                "ContentDate": {"Start": "2025-01-01T00:00:00Z"},
                "BurstId": 123,
                "coverage": 33.2,
                "SwathIdentifier": "IW1",
            }
        ]
    )
    stats = {"total_acquisitions": 1}
    result = validate_burst_results(df, stats)
    assert result["ok"] is True
    assert result["errors"] == []


def test_debug_burst_summary_content():
    df = pd.DataFrame(
        [
            {"Id": "a", "SwathIdentifier": "IW1", "coverage": 10.0},
            {"Id": "b", "SwathIdentifier": "IW2", "coverage": 20.0},
        ]
    )
    stats = {"total_acquisitions": 2}
    orbit = {"orbit_direction": "DESCENDING", "relative_orbit": 66}
    dbg = debug_burst_summary(df, stats, orbit)
    assert dbg["rows"] == 2
    assert dbg["orbit_direction"] == "DESCENDING"
    assert dbg["relative_orbit"] == 66
    assert dbg["coverage"]["max"] == 20.0


@patch("phidown.insar_workflow._save_coverage_plot")
def test_save_workflow_outputs_writes_expected_files(mock_plot, tmp_path):
    coverage_path = tmp_path / "coverage_results.png"
    mock_plot.return_value = coverage_path

    paths = save_workflow_outputs(
        df=None,
        stats={"total_acquisitions": 2},
        validation={"ok": True},
        debug={"rows": 0},
        orbit={"orbit_direction": "ASCENDING"},
        output_dir=str(tmp_path),
        save_results_csv=True,
    )

    assert paths["search_results_csv"] == tmp_path / "search_results.csv"
    assert paths["coverage_plot_png"] == coverage_path
    assert (tmp_path / "temporal_statistics.json").exists()
    assert (tmp_path / "validation_report.json").exists()
    assert (tmp_path / "debug_summary.json").exists()


def test_save_coverage_plot_returns_none_without_coverage(tmp_path):
    df = pd.DataFrame([{"Id": "1"}])

    assert _save_coverage_plot(df, Path(tmp_path)) is None


@patch("phidown.insar_workflow.save_workflow_outputs")
@patch("phidown.insar_workflow.debug_burst_summary")
@patch("phidown.insar_workflow.validate_burst_results")
@patch("phidown.insar_workflow.compute_burst_statistics")
@patch("phidown.insar_workflow.search_bursts")
@patch("phidown.insar_workflow.find_orbit_configuration")
@patch("phidown.insar_workflow.CopernicusDataSearcher")
def test_run_burst_workflow_orchestrates_helpers(
    mock_searcher_class,
    mock_find_orbit,
    mock_search_bursts,
    mock_compute_stats,
    mock_validate_results,
    mock_debug_summary,
    mock_save_outputs,
    tmp_path,
):
    df = pd.DataFrame([{"Id": "1"}])
    orbit = {"orbit_direction": "DESCENDING", "relative_orbit": 66}
    stats = {"total_acquisitions": 1}
    validation = {"ok": True, "errors": [], "warnings": []}
    debug = {"rows": 1}

    mock_find_orbit.return_value = orbit
    mock_search_bursts.return_value = df
    mock_compute_stats.return_value = stats
    mock_validate_results.return_value = validation
    mock_debug_summary.return_value = debug
    mock_save_outputs.return_value = {"search_results_csv": tmp_path / "search_results.csv"}

    result = run_burst_workflow(
        {
            "search": {
                "aoi_wkt": "POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))",
                "start_date": "2025-01-01T00:00:00",
                "end_date": "2025-01-10T00:00:00",
            },
            "output_statistics": str(tmp_path),
        }
    )

    assert result["df"].equals(df)
    assert result["orbit"] == orbit
    assert result["stats"] == stats
    assert result["validation"] == validation
    assert result["debug"] == debug
    mock_searcher_class.assert_called_once()
    mock_save_outputs.assert_called_once()
