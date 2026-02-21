from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from .search import CopernicusDataSearcher

try:
    import matplotlib.pyplot as plt
    _MATPLOTLIB_AVAILABLE = True
except ImportError:
    _MATPLOTLIB_AVAILABLE = False


@dataclass
class BurstSearchConfig:
    aoi_wkt: str
    start_date: str
    end_date: str
    polarisation: str = "VV"
    orbit_direction: Optional[str] = None
    relative_orbit: Optional[int] = None
    platforms: List[str] = field(default_factory=lambda: ["all"])
    swath_identifier: Optional[str] = None
    burst_id: Optional[int] = None
    max_results: int = 1000

    def __post_init__(self) -> None:
        self.polarisation = self.polarisation.upper()
        if self.polarisation not in {"VV", "VH", "HH", "HV"}:
            raise ValueError(f"Invalid polarisation: {self.polarisation}")
        if self.orbit_direction:
            self.orbit_direction = self.orbit_direction.upper()
            if self.orbit_direction not in {"ASCENDING", "DESCENDING"}:
                raise ValueError(f"Invalid orbit_direction: {self.orbit_direction}")
        if isinstance(self.platforms, str):
            self.platforms = [self.platforms]
        self.platforms = [p.upper() for p in self.platforms]
        for p in self.platforms:
            if p not in {"A", "B", "C", "D", "ALL"}:
                raise ValueError(f"Invalid platform: {p}")


@dataclass
class BurstWorkflowConfig:
    search: BurstSearchConfig
    output_statistics: Optional[str] = None
    save_results_csv: bool = True


def build_burst_workflow_config(config: Dict[str, Any]) -> BurstWorkflowConfig:
    search = config.get("search", {})
    return BurstWorkflowConfig(
        search=BurstSearchConfig(
            aoi_wkt=search.get("aoi_wkt", ""),
            start_date=search.get("start_date", ""),
            end_date=search.get("end_date", ""),
            polarisation=search.get("polarisation", "VV"),
            orbit_direction=search.get("orbit_direction"),
            relative_orbit=search.get("relative_orbit"),
            platforms=search.get("platforms", ["all"]),
            swath_identifier=search.get("swath_identifier"),
            burst_id=search.get("burst_id"),
            max_results=search.get("max_results", 1000),
        ),
        output_statistics=config.get("output_statistics"),
        save_results_csv=config.get("save_results_csv", True),
    )


def _platform_filter(platforms: List[str]) -> Optional[str]:
    if "ALL" in platforms:
        return None
    if len(platforms) == 1:
        return platforms[0]
    return None


def find_orbit_configuration(cfg: BurstSearchConfig, searcher: Optional[CopernicusDataSearcher] = None) -> Dict[str, Any]:
    local_searcher = searcher or CopernicusDataSearcher()
    analysis = local_searcher.find_optimal_orbit(
        aoi_wkt=cfg.aoi_wkt,
        start_date=cfg.start_date,
        end_date=cfg.end_date,
        product_type="SLC",
        top=cfg.max_results,
    )
    rec = analysis.get("recommended") or {}
    return {
        "analysis": analysis,
        "orbit_direction": cfg.orbit_direction or rec.get("orbit_direction"),
        "relative_orbit": cfg.relative_orbit if cfg.relative_orbit is not None else rec.get("relative_orbit"),
    }


def search_bursts(cfg: BurstSearchConfig, searcher: Optional[CopernicusDataSearcher] = None) -> pd.DataFrame:
    local_searcher = searcher or CopernicusDataSearcher()
    orbit = find_orbit_configuration(cfg, searcher=local_searcher)
    orbit_direction = orbit.get("orbit_direction")
    relative_orbit = orbit.get("relative_orbit")

    platform = _platform_filter(cfg.platforms)
    local_searcher.query_by_filter(
        burst_mode=True,
        orbit_direction=orbit_direction,
        relative_orbit_number=relative_orbit,
        aoi_wkt=cfg.aoi_wkt,
        start_date=cfg.start_date,
        end_date=cfg.end_date,
        polarisation_channels=cfg.polarisation,
        platform_serial_identifier=platform,
        swath_identifier=cfg.swath_identifier,
        burst_id=cfg.burst_id,
        top=cfg.max_results,
        count=True,
    )
    df = local_searcher.execute_query()

    if df is None or df.empty:
        return pd.DataFrame()

    if "ALL" not in cfg.platforms and len(cfg.platforms) > 1 and "PlatformSerialIdentifier" in df.columns:
        df = df[df["PlatformSerialIdentifier"].isin(cfg.platforms)]

    swath_priority = {"IW1": 0, "IW2": 1, "IW3": 2}
    if "SwathIdentifier" in df.columns:
        df["subswath_priority"] = df["SwathIdentifier"].apply(lambda x: swath_priority.get(x, 99))
    else:
        df["subswath_priority"] = 99

    sort_cols: List[str] = []
    sort_asc: List[bool] = []
    if "coverage" in df.columns:
        sort_cols.append("coverage")
        sort_asc.append(False)
    sort_cols.append("subswath_priority")
    sort_asc.append(True)

    return df.sort_values(sort_cols, ascending=sort_asc).reset_index(drop=True)


def compute_burst_statistics(df: pd.DataFrame, searcher: Optional[CopernicusDataSearcher] = None) -> Dict[str, Any]:
    local_searcher = searcher or CopernicusDataSearcher()
    return local_searcher.compute_temporal_statistics(df)


def validate_burst_results(df: pd.DataFrame, stats: Dict[str, Any]) -> Dict[str, Any]:
    errors: List[str] = []
    warnings: List[str] = []

    if df is None or df.empty:
        errors.append("No burst results found.")
    else:
        if "Id" not in df.columns:
            errors.append("Missing required column: Id")
        if "GeoFootprint" not in df.columns and "Footprint" not in df.columns:
            errors.append("Missing required footprint column: GeoFootprint or Footprint")
        if "ContentDate" not in df.columns and "OriginDate" not in df.columns:
            errors.append("Missing required date column: ContentDate or OriginDate")
        if "BurstId" not in df.columns:
            warnings.append("BurstId column not found.")
        if "coverage" in df.columns and df["coverage"].notna().sum() == 0:
            warnings.append("Coverage column exists but contains only null values.")

    if not stats:
        warnings.append("Temporal statistics are empty.")
    elif "total_acquisitions" not in stats:
        errors.append("Temporal statistics missing total_acquisitions.")

    return {"ok": len(errors) == 0, "errors": errors, "warnings": warnings}


def debug_burst_summary(df: pd.DataFrame, stats: Dict[str, Any], orbit: Dict[str, Any]) -> Dict[str, Any]:
    summary: Dict[str, Any] = {
        "rows": int(len(df)) if df is not None else 0,
        "columns": list(df.columns) if df is not None else [],
        "orbit_direction": orbit.get("orbit_direction"),
        "relative_orbit": orbit.get("relative_orbit"),
        "stats_keys": list(stats.keys()) if isinstance(stats, dict) else [],
    }

    if df is not None and not df.empty:
        if "SwathIdentifier" in df.columns:
            summary["swath_distribution"] = {str(k): int(v) for k, v in df["SwathIdentifier"].value_counts().items()}
        if "coverage" in df.columns and df["coverage"].notna().any():
            summary["coverage"] = {
                "min": float(df["coverage"].min()),
                "max": float(df["coverage"].max()),
                "mean": float(df["coverage"].mean()),
            }
    return summary


def save_workflow_outputs(
    df: pd.DataFrame,
    stats: Dict[str, Any],
    validation: Dict[str, Any],
    debug: Dict[str, Any],
    orbit: Optional[Dict[str, Any]],
    output_dir: str,
    save_results_csv: bool = True,
) -> Dict[str, Path]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths: Dict[str, Path] = {}

    if save_results_csv:
        csv_path = out / "search_results.csv"
        df.to_csv(csv_path, index=False)
        paths["search_results_csv"] = csv_path

    stats_path = out / "temporal_statistics.json"
    stats_path.write_text(json.dumps(stats, indent=2, default=str))
    paths["temporal_statistics_json"] = stats_path

    validation_path = out / "validation_report.json"
    validation_path.write_text(json.dumps(validation, indent=2))
    paths["validation_report_json"] = validation_path

    debug_path = out / "debug_summary.json"
    debug_path.write_text(json.dumps(debug, indent=2, default=str))
    paths["debug_summary_json"] = debug_path

    coverage_plot_path = _save_coverage_plot(df, out, orbit=orbit)
    if coverage_plot_path is not None:
        paths["coverage_plot_png"] = coverage_plot_path

    return paths


def _save_coverage_plot(
    df: pd.DataFrame,
    output_dir: Path,
    orbit: Optional[Dict[str, Any]] = None,
) -> Optional[Path]:
    """Save a diagnostics plot with orbit recommendation and burst coverage details."""
    if not _MATPLOTLIB_AVAILABLE or df is None or df.empty or "coverage" not in df.columns:
        return None

    cov = pd.to_numeric(df["coverage"], errors="coerce").dropna()
    if cov.empty:
        return None

    ranked_idx = cov.sort_values(ascending=False).index
    ranked = cov.loc[ranked_idx].reset_index(drop=True)
    ranked_df = df.loc[ranked_idx].copy()
    fig, axes = plt.subplots(2, 2, figsize=(14, 9))

    analysis = (orbit or {}).get("analysis", {})
    asc = analysis.get("ascending", {}) if isinstance(analysis, dict) else {}
    desc = analysis.get("descending", {}) if isinstance(analysis, dict) else {}
    rec = analysis.get("recommended", {}) if isinstance(analysis, dict) else {}

    # 1) Ascending vs Descending best coverage comparison
    ax0 = axes[0, 0]
    dir_labels = ["ASCENDING", "DESCENDING"]
    dir_values = [float(asc.get("max_coverage", 0) or 0), float(desc.get("max_coverage", 0) or 0)]
    bars = ax0.bar(dir_labels, dir_values, color=["#4c78a8", "#f58518"], alpha=0.9)
    ax0.set_title("Best Direction by Avg AOI Coverage")
    ax0.set_ylabel("Coverage (%)")
    ax0.grid(True, alpha=0.25, axis="y")
    for bar, value in zip(bars, dir_values):
        ax0.text(bar.get_x() + bar.get_width() / 2, value + 0.8, f"{value:.1f}%", ha="center", va="bottom")
    if rec:
        ax0.text(
            0.02,
            0.98,
            (
                f"Recommended: {rec.get('orbit_direction')} | "
                f"Orbit #{rec.get('relative_orbit')} | "
                f"Expected {float(rec.get('expected_coverage', 0)):.1f}%"
            ),
            transform=ax0.transAxes,
            va="top",
            ha="left",
            fontsize=9,
            bbox=dict(facecolor="white", edgecolor="gray", alpha=0.8),
        )

    # 2) Top relative orbits per direction from orbit analysis
    ax1 = axes[0, 1]
    orbit_labels: List[str] = []
    orbit_values: List[float] = []
    orbit_colors: List[str] = []
    for label, color, payload in (("ASC", "#4c78a8", asc), ("DES", "#f58518", desc)):
        orbits = payload.get("orbits", {}) if isinstance(payload, dict) else {}
        top_items = sorted(orbits.items(), key=lambda kv: float((kv[1] or {}).get("avg_coverage", 0)), reverse=True)[:3]
        for orb, vals in top_items:
            orbit_labels.append(f"{label} #{orb}")
            orbit_values.append(float((vals or {}).get("avg_coverage", 0)))
            orbit_colors.append(color)
    if orbit_labels:
        bars1 = ax1.bar(orbit_labels, orbit_values, color=orbit_colors, alpha=0.9)
        for bar, value in zip(bars1, orbit_values):
            ax1.text(bar.get_x() + bar.get_width() / 2, value + 0.8, f"{value:.1f}%", ha="center", va="bottom", fontsize=8)
    else:
        ax1.text(0.5, 0.5, "Orbit analysis not available", ha="center", va="center")
    ax1.set_title("Top Relative Orbits by Direction")
    ax1.set_ylabel("Avg Coverage (%)")
    ax1.grid(True, alpha=0.25, axis="y")
    ax1.tick_params(axis="x", rotation=20)

    # 3) Top burst IDs by max coverage in selected result set
    ax2 = axes[1, 0]
    if "BurstId" in ranked_df.columns:
        burst_cov = (
            ranked_df.assign(coverage_num=pd.to_numeric(ranked_df["coverage"], errors="coerce"))
            .dropna(subset=["coverage_num"])
            .groupby("BurstId", dropna=True)["coverage_num"]
            .max()
            .sort_values(ascending=False)
            .head(10)
        )
        if not burst_cov.empty:
            labels = [str(b) for b in burst_cov.index]
            vals = burst_cov.values.tolist()
            xpos = list(range(len(labels)))
            bars2 = ax2.bar(xpos, vals, color="#54a24b", alpha=0.9)
            ax2.set_xticks(xpos)
            ax2.set_xticklabels(labels)
            for bar, value in zip(bars2, vals):
                ax2.text(bar.get_x() + bar.get_width() / 2, value + 0.8, f"{value:.1f}", ha="center", va="bottom", fontsize=8)
            ax2.tick_params(axis="x", rotation=30)
        else:
            ax2.text(0.5, 0.5, "No BurstId coverage data", ha="center", va="center")
    else:
        ax2.text(0.5, 0.5, "BurstId column not available", ha="center", va="center")
    ax2.set_title("Top Burst IDs by Coverage")
    ax2.set_ylabel("Coverage (%)")
    ax2.grid(True, alpha=0.25, axis="y")

    # 4) Coverage distribution in selected result set
    ax3 = axes[1, 1]
    ax3.hist(cov, bins=min(20, max(5, int(cov.shape[0] ** 0.5))), color="steelblue", edgecolor="black", alpha=0.8)
    ax3.axvline(cov.mean(), color="red", linestyle="--", linewidth=1.5, label=f"Mean {cov.mean():.1f}%")
    ax3.axvline(cov.max(), color="green", linestyle="--", linewidth=1.5, label=f"Max {cov.max():.1f}%")
    ax3.set_title("Coverage Distribution (Selected Search)")
    ax3.set_xlabel("Coverage (%)")
    ax3.set_ylabel("Count")
    ax3.grid(True, alpha=0.25, axis="y")
    ax3.legend(loc="best", fontsize=8)

    fig.tight_layout()
    out_path = output_dir / "coverage_results.png"
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out_path


def run_burst_workflow(config: Dict[str, Any]) -> Dict[str, Any]:
    wf_cfg = build_burst_workflow_config(config)
    searcher = CopernicusDataSearcher()
    orbit = find_orbit_configuration(wf_cfg.search, searcher=searcher)
    df = search_bursts(wf_cfg.search, searcher=searcher)
    stats = compute_burst_statistics(df, searcher=searcher)
    validation = validate_burst_results(df, stats)
    debug = debug_burst_summary(df, stats, orbit)

    paths: Dict[str, Path] = {}
    if wf_cfg.output_statistics:
        paths = save_workflow_outputs(
            df=df,
            stats=stats,
            validation=validation,
            debug=debug,
            orbit=orbit,
            output_dir=wf_cfg.output_statistics,
            save_results_csv=wf_cfg.save_results_csv,
        )

    return {
        "df": df,
        "stats": stats,
        "orbit": orbit,
        "validation": validation,
        "debug": debug,
        "paths": paths,
    }
