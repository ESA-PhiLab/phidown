import pandas as pd

from phidown.insar_workflow import (
    build_burst_workflow_config,
    validate_burst_results,
    debug_burst_summary,
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
