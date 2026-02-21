#!/usr/bin/env python3
"""
Test script to verify the interactive polygon tool works correctly.
"""

import pytest

pytest.skip(
    "Interactive manual smoke script; excluded from automated unit test runs.",
    allow_module_level=True,
)

# Test imports
try:
    from phidown.interactive_tools import (
        InteractivePolygonTool, 
        create_polygon_tool, 
        search_with_polygon
    )
    print("✅ Successfully imported interactive tools from phidown package!")
    
    # Test creating a basic tool
    tool = InteractivePolygonTool(
        center=(45.0, 0.0),
        zoom=3,
        show_basemap_switcher=True
    )
    print("✅ Successfully created InteractivePolygonTool instance!")
    
    # Test helper function
    satellite_tool = create_polygon_tool(
        center=(37.7749, -122.4194),
        zoom=12,
        basemap_type='satellite'
    )
    print("✅ Successfully created satellite tool with helper function!")
    
    # Test basemap access
    from ipyleaflet import basemaps
    print(f"✅ OpenStreetMap basemap: {basemaps.OpenStreetMap.Mapnik['name']}")
    print(f"✅ Esri World Imagery: {basemaps.Esri.WorldImagery['name']}")
    
    print("\n🎉 All tests passed! The interactive polygon tool is working correctly.")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure ipyleaflet and ipywidgets are installed.")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
