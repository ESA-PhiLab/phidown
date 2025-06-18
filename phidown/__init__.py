# __init__.py

"""
Package Initialization
"""

__version__ = "0.1.13"
__author__ = "Roberto Del Prete"

# Import main classes and functions
from .search import CopernicusDataSearcher  
from .viz import plot_kml_coordinates

# Note: Downloader functions are available but not imported at package level
# to avoid module execution conflicts. Import them directly if needed:
# from phidown.downloader import pull_down, load_credentials, get_access_token

# Import interactive tools (optional dependency)  
try:
    from .interactive_tools import InteractivePolygonTool, create_polygon_tool, search_with_polygon
    __all__ = [
        'CopernicusDataSearcher',
        'plot_kml_coordinates',
        'InteractivePolygonTool',
        'create_polygon_tool', 
        'search_with_polygon'
    ]
except ImportError:
    # ipyleaflet and ipywidgets not available
    __all__ = [
        'CopernicusDataSearcher',
        'plot_kml_coordinates'
    ]
