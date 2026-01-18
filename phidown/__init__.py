# __init__.py

"""
Package Initialization
"""

__version__ = "0.1.19"
__author__ = "Roberto Del Prete"

# Import main classes and functions
from .search import CopernicusDataSearcher  
from .viz import plot_kml_coordinates

# Lazy import CLI functions to avoid import conflicts
# These will be imported on first use
def __getattr__(name):
    """Lazy import for CLI functions."""
    if name == 'download_by_name':
        from .cli import download_by_name
        return download_by_name
    elif name == 'download_by_s3path':
        from .cli import download_by_s3path
        return download_by_s3path
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

# Import AIS functionality (optional dependency)
try:
    from .ais import AISDataHandler, download_ais_data
    _AIS_AVAILABLE = True
except ImportError:
    # huggingface_hub not available
    _AIS_AVAILABLE = False

# Note: Downloader functions are available but not imported at package level
# to avoid module execution conflicts. Import them directly if needed:
# from phidown.downloader import pull_down, load_credentials, get_access_token

# Import interactive tools (optional dependency)  
try:
    from .interactive_tools import InteractivePolygonTool, create_polygon_tool, search_with_polygon
    _INTERACTIVE_AVAILABLE = True
except ImportError:
    # ipyleaflet and ipywidgets not available
    _INTERACTIVE_AVAILABLE = False

# Build __all__ dynamically based on available dependencies
__all__ = [
    'CopernicusDataSearcher',
    'plot_kml_coordinates',
    'download_by_name',
    'download_by_s3path'
]

if _AIS_AVAILABLE:
    __all__.extend(['AISDataHandler', 'download_ais_data'])

if _INTERACTIVE_AVAILABLE:
    __all__.extend(['InteractivePolygonTool', 'create_polygon_tool', 'search_with_polygon'])
