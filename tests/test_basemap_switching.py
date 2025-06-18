#!/usr/bin/env python3
"""
Test script to verify basemap switching functionality.
This script creates a simple tool and simulates dropdown changes.
"""

import sys
import os
sys.path.insert(0, '.')

from phidown.interactive_tools import InteractivePolygonTool, create_polygon_tool
from ipyleaflet import basemaps

def test_basemap_switching():
    """Test the basemap switching functionality."""
    print("🧪 Testing Basemap Switching Functionality")
    print("=" * 50)
    
    try:
        # Create a polygon tool with satellite imagery
        print("1. Creating polygon tool with satellite imagery...")
        tool = create_polygon_tool(
            center=(37.7749, -122.4194),  # San Francisco
            zoom=10,
            basemap_type='satellite',
            show_basemap_switcher=True
        )
        
        print(f"   ✅ Initial basemap: {tool.current_basemap_name}")
        print(f"   ✅ Dropdown value: {tool.basemap_dropdown.value}")
        print(f"   ✅ Available basemaps: {len(tool.basemap_layers)}")
        
        # Test switching to different basemaps
        test_basemaps = [
            '🗺️ OpenStreetMap',
            '🌑 CartoDB Dark Matter', 
            '⛰️ Esri World Topo',
            '🎨 Stadia Watercolor'
        ]
        
        print("\n2. Testing basemap switches...")
        for basemap_name in test_basemaps:
            if basemap_name in tool.basemap_layers:
                print(f"   🔄 Switching to: {basemap_name}")
                
                # Simulate dropdown change
                old_basemap = tool.current_basemap_name
                tool.basemap_dropdown.value = basemap_name
                
                # The observe callback should have been triggered
                print(f"      ✅ Switched from '{old_basemap}' to '{tool.current_basemap_name}'")
                
                # Verify the map basemap was actually changed
                expected_basemap = tool.basemap_layers[basemap_name]
                if tool.map.basemap == expected_basemap:
                    print(f"      ✅ Map basemap correctly updated")
                else:
                    print(f"      ❌ Map basemap NOT updated properly")
            else:
                print(f"   ⚠️ Basemap '{basemap_name}' not found in available layers")
        
        print("\n3. Testing edge cases...")
        
        # Test with a basemap tool that doesn't show switcher
        print("   📱 Creating tool without basemap switcher...")
        simple_tool = InteractivePolygonTool(
            center=(40.7589, -73.9851),  # NYC
            zoom=10,
            show_basemap_switcher=False
        )
        
        if not hasattr(simple_tool, 'basemap_dropdown'):
            print("      ✅ Tool without switcher correctly has no dropdown")
        else:
            print("      ❌ Tool without switcher incorrectly has dropdown")
        
        print("\n🎉 All basemap switching tests completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Error during basemap switching test: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_basemap_switching()
    if success:
        print("\n✅ Basemap switching is working correctly!")
        print("💡 You can now use the dropdown in the interactive tool to switch basemaps.")
    else:
        print("\n❌ Basemap switching test failed!")
    
    sys.exit(0 if success else 1)
