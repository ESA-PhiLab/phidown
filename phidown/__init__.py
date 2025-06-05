# __init__.py

"""
Package Initialization
"""

__version__ = "0.1.13"
__author__ = "Roberto Del Prete"

# Import main classes and functions
from .search import CopernicusDataSearcher
from .downloader import pull_down, load_credentials, get_access_token
from .viz import plot_kml_coordinates

# Import interactive tools (optional dependency)
try:
    from .interactive_tools import InteractivePolygonTool, create_polygon_tool, search_with_polygon
    __all__ = [
        'CopernicusDataSearcher', 
        'pull_down',
        'load_credentials',
        'get_access_token',
        'plot_kml_coordinates',
        'InteractivePolygonTool',
        'create_polygon_tool',
        'search_with_polygon'
    ]
except ImportError:
    # ipyleaflet and ipywidgets not available
    __all__ = [
        'CopernicusDataSearcher', 
        'pull_down',
        'load_credentials', 
        'get_access_token',
        'plot_kml_coordinates'
    ]
