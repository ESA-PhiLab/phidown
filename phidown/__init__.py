"""Top-level package exports for phidown."""

from __future__ import annotations

from importlib import import_module
from importlib.util import find_spec
import sys
from typing import Dict, Iterable, Tuple

__version__ = "0.1.25"
__author__ = "Roberto Del Prete"

_LAZY_EXPORTS: Dict[str, Tuple[str, str]] = {
    "CopernicusDataSearcher": ("phidown.search", "CopernicusDataSearcher"),
    "plot_kml_coordinates": ("phidown.viz", "plot_kml_coordinates"),
    "plot_product_footprints": ("phidown.viz", "plot_product_footprints"),
    "BurstSearchConfig": ("phidown.insar_workflow", "BurstSearchConfig"),
    "BurstWorkflowConfig": ("phidown.insar_workflow", "BurstWorkflowConfig"),
    "build_burst_workflow_config": ("phidown.insar_workflow", "build_burst_workflow_config"),
    "run_burst_workflow": ("phidown.insar_workflow", "run_burst_workflow"),
    "validate_burst_results": ("phidown.insar_workflow", "validate_burst_results"),
    "debug_burst_summary": ("phidown.insar_workflow", "debug_burst_summary"),
    "download_by_name": ("phidown.cli", "download_by_name"),
    "download_by_s3path": ("phidown.cli", "download_by_s3path"),
    "AISDataHandler": ("phidown.ais", "AISDataHandler"),
    "download_ais_data": ("phidown.ais", "download_ais_data"),
    "InteractivePolygonTool": ("phidown.interactive_tools", "InteractivePolygonTool"),
    "create_polygon_tool": ("phidown.interactive_tools", "create_polygon_tool"),
    "search_with_polygon": ("phidown.interactive_tools", "search_with_polygon"),
}

_OPTIONAL_DEPENDENCIES: Dict[str, Tuple[str, ...]] = {
    "plot_kml_coordinates": ("folium",),
    "plot_product_footprints": ("folium",),
    "AISDataHandler": ("huggingface_hub",),
    "download_ais_data": ("huggingface_hub",),
    "InteractivePolygonTool": ("ipyleaflet", "ipywidgets", "shapely"),
    "create_polygon_tool": ("ipyleaflet", "ipywidgets", "shapely"),
    "search_with_polygon": ("ipyleaflet", "ipywidgets", "shapely"),
}

_BASE_EXPORTS = [
    "CopernicusDataSearcher",
    "BurstSearchConfig",
    "BurstWorkflowConfig",
    "build_burst_workflow_config",
    "run_burst_workflow",
    "validate_burst_results",
    "debug_burst_summary",
    "download_by_name",
    "download_by_s3path",
]


def _dependencies_available(dependencies: Iterable[str]) -> bool:
    """Check whether the named import dependencies are importable."""
    for name in dependencies:
        if name in sys.modules:
            continue
        try:
            if find_spec(name) is None:
                return False
        except (ImportError, ValueError):
            return False
    return True


def _optional_import_error(name: str, dependencies: Tuple[str, ...]) -> ImportError:
    joined = ", ".join(dependencies)
    return ImportError(f"{name} requires optional dependencies: {joined}")


def __getattr__(name: str):
    """Resolve public exports lazily to avoid eager optional imports."""
    if name not in _LAZY_EXPORTS:
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

    dependencies = _OPTIONAL_DEPENDENCIES.get(name)
    if dependencies and not _dependencies_available(dependencies):
        raise _optional_import_error(name, dependencies)

    module_name, attribute_name = _LAZY_EXPORTS[name]
    module = import_module(module_name)
    return getattr(module, attribute_name)


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(_LAZY_EXPORTS))


__all__ = list(_BASE_EXPORTS)
for export_name, dependencies in _OPTIONAL_DEPENDENCIES.items():
    if _dependencies_available(dependencies):
        __all__.append(export_name)
