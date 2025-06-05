"""
Interactive polygon drawing tool for geospatial analysis using ipyleaflet.

This module provides the InteractivePolygonTool class for drawing polygons on 
interactive maps with real-time WKT export functionality, multiple basemap 
layers, and seamless integration with phidown search capabilities.
"""

from ipyleaflet import (
    Map, 
    DrawControl, 
    GeoJSON, 
    LayersControl,
    basemaps,
    Marker,
    Popup
)
from ipywidgets import (
    VBox, 
    HBox, 
    Button, 
    Output, 
    HTML, 
    Textarea,
    Label,
    Layout,
    Dropdown
)
import json
from shapely.geometry import Polygon, mapping
from shapely import wkt
from typing import List, Dict, Any, Optional

# Import pandas for type annotations (optional dependency)
try:
    import pandas
except ImportError:
    pandas = None


class InteractivePolygonTool:
    """
    Interactive polygon drawing tool using ipyleaflet.
    
    This class provides functionality to draw polygons on an interactive map,
    extract coordinates in WKT format, and manage multiple polygons with 
    comprehensive basemap support.
    
    Attributes:
        map (Map): The ipyleaflet map widget
        draw_control (DrawControl): Drawing control for the map
        output (Output): Output widget for displaying information
        wkt_output (Textarea): Text area for WKT output
        polygons (List[Dict]): List of drawn polygons with metadata
        basemap_layers (Dict): Dictionary of available basemap layers
        show_basemap_switcher (bool): Whether to show basemap switcher controls
    """
    
    def __init__(self, center: tuple = (45.0, 0.0), zoom: int = 2, 
                 basemap=basemaps.OpenStreetMap.Mapnik, show_basemap_switcher: bool = True):
        """
        Initialize the interactive polygon tool.
        
        Args:
            center (tuple): Initial map center coordinates (lat, lon)
            zoom (int): Initial zoom level
            basemap: Initial basemap to use for the map
            show_basemap_switcher (bool): Whether to show basemap switcher controls
        """
        self.polygons: List[Dict[str, Any]] = []
        self.show_basemap_switcher = show_basemap_switcher
        self.current_basemap = basemap
        self._setup_basemap_layers()
        self._setup_map(center, zoom, basemap)
        self._setup_controls()
        self._setup_ui()
    
    def _setup_basemap_layers(self) -> None:
        """
        Setup available basemap layers organized by categories.
        """
        self.basemap_layers = {
            # === SATELLITE & IMAGERY ===
            '🛰️ Esri World Imagery': basemaps.Esri.WorldImagery,
            '🌍 NASA Blue Marble': basemaps.NASAGIBS.BlueMarble,
            '🌙 NASA Earth at Night': basemaps.NASAGIBS.ViirsEarthAtNight2012,
            '🛰️ NASA MODIS True Color': basemaps.NASAGIBS.ModisTerraTrueColorCR,
            '🛰️ NASA VIIRS True Color': basemaps.NASAGIBS.ViirsTrueColorCR,
            '🛰️ Stadia Satellite': basemaps.Stadia.AlidadeSatellite,
            
            # === STREET & ROAD MAPS ===
            '🗺️ OpenStreetMap': basemaps.OpenStreetMap.Mapnik,
            '🗺️ Esri World Street': basemaps.Esri.WorldStreetMap,
            '🗺️ CartoDB Positron': basemaps.CartoDB.Positron,
            '🗺️ CartoDB Voyager': basemaps.CartoDB.Voyager,
            '🗺️ Stadia OSM Bright': basemaps.Stadia.OSMBright,
            '🗺️ Stadia Alidade Smooth': basemaps.Stadia.AlidadeSmooth,
            
            # === TOPOGRAPHIC & TERRAIN ===
            '⛰️ Esri World Topo': basemaps.Esri.WorldTopoMap,
            '⛰️ Esri World Terrain': basemaps.Esri.WorldTerrain,
            '⛰️ Esri World Physical': basemaps.Esri.WorldPhysical,
            '⛰️ Esri Shaded Relief': basemaps.Esri.WorldShadedRelief,
            '⛰️ Stadia Terrain': basemaps.Stadia.StamenTerrain,
            '⛰️ Stadia Outdoors': basemaps.Stadia.Outdoors,
            '⛰️ OpenTopoMap': basemaps.OpenTopoMap,
            
            # === DARK THEMES ===
            '🌑 CartoDB Dark Matter': basemaps.CartoDB.DarkMatter,
            '🌑 Stadia Alidade Dark': basemaps.Stadia.AlidadeSmoothDark,
            '🌑 Stadia Toner': basemaps.Stadia.StamenToner,
            
            # === ARTISTIC & SPECIAL ===
            '🎨 Stadia Watercolor': basemaps.Stadia.StamenWatercolor,
            '🗺️ Esri National Geographic': basemaps.Esri.NatGeoWorldMap,
            '🌊 Esri Ocean Basemap': basemaps.Esri.OceanBasemap,
            '🌫️ Esri World Gray Canvas': basemaps.Esri.WorldGrayCanvas,
            
            # === SPECIALIZED ===
            '❄️ Esri Arctic Imagery': basemaps.Esri.ArcticImagery,
            '🧊 NASA Ice Velocity': basemaps.NASAGIBS.MEaSUREsIceVelocity3031,
            '🌡️ NASA Land Surface Temp': basemaps.NASAGIBS.ModisTerraLSTDay,
            '☁️ NASA Snow Cover': basemaps.NASAGIBS.ModisTerraSnowCover
        }

    def print_available_basemaps(self, max_items: int = 10) -> None:
        """
        Print the available basemaps in a formatted way.
        """
        print("Available Basemaps:")
        for i, (name, layer) in enumerate(self.basemap_layers.items()):
            if i >= max_items:
                break
            print(f" - {name}")

    def _setup_map(self, center: tuple, zoom: int, basemap) -> None:
        """
        Setup the main map widget.
        
        Args:
            center (tuple): Map center coordinates
            zoom (int): Initial zoom level
            basemap: Basemap to use
        """
        self.map = Map(
            center=center,
            zoom=zoom,
            basemap=basemap,
            scroll_wheel_zoom=True,
            layout=Layout(height='500px', width='100%')
        )
        
        # Add layer control
        layers_control = LayersControl(position='topright')
        self.map.add_control(layers_control)
        
        # Store the current basemap name for dropdown sync
        self.current_basemap_name = self._get_basemap_name(basemap)
    
    def _get_basemap_name(self, basemap) -> str:
        """
        Get the display name for a basemap object.
        
        Args:
            basemap: The basemap object
            
        Returns:
            str: The display name of the basemap
        """
        # Find the basemap name by comparing the basemap object
        for name, layer in self.basemap_layers.items():
            if layer == basemap:
                return name
        # Default fallback
        return '🗺️ OpenStreetMap'
    
    def _setup_controls(self) -> None:
        """
        Setup drawing controls for the map.
        """
        self.draw_control = DrawControl(
            polygon={
                'shapeOptions': {
                    'fillColor': '#3388ff',
                    'color': '#0000ff',
                    'fillOpacity': 0.3,
                    'weight': 2
                }
            },
            rectangle={
                'shapeOptions': {
                    'fillColor': '#ff3333',
                    'color': '#ff0000',
                    'fillOpacity': 0.3,
                    'weight': 2
                }
            },
            polyline={},
            circle={},
            circlemarker={},
            marker={},
            edit=True,
            remove=True
        )
        
        # Add event handlers using observe method
        self.draw_control.on_draw(self._handle_draw)
        # For edit and delete, we'll use a single observer on the data attribute
        self.draw_control.observe(self._handle_data_change, names=['data'])
        
        self.map.add_control(self.draw_control)
    
    def _setup_ui(self) -> None:
        """
        Setup the user interface widgets.
        """
        # Output widget for messages
        self.output = Output()
        
        # WKT output textarea
        self.wkt_output = Textarea(
            placeholder='WKT coordinates will appear here...',
            description='WKT Output:',
            layout=Layout(height='100px', width='100%'),
            style={'description_width': 'initial'}
        )
        
        # Control buttons
        self.clear_button = Button(
            description='Clear All',
            button_style='warning',
            icon='trash'
        )
        self.clear_button.on_click(self._clear_all)
        
        self.copy_button = Button(
            description='Copy WKT',
            button_style='info',
            icon='copy'
        )
        self.copy_button.on_click(self._copy_wkt)
        
        # Basemap switcher if enabled
        if self.show_basemap_switcher:
            self.basemap_dropdown = Dropdown(
                options=list(self.basemap_layers.keys()),
                value=self.current_basemap_name,
                description='Basemap:',
                style={'description_width': 'initial'}
            )
            self.basemap_dropdown.observe(self._change_basemap, names='value')
        
        # Load WKT functionality
        self.wkt_input = Textarea(
            placeholder='Paste WKT string here to visualize...',
            description='Load WKT:',
            layout=Layout(height='80px', width='100%'),
            style={'description_width': 'initial'}
        )
        
        self.load_button = Button(
            description='Load WKT',
            button_style='success',
            icon='upload'
        )
        self.load_button.on_click(self._load_wkt)
    
    def _change_basemap(self, change) -> None:
        """
        Change the basemap when dropdown selection changes.
        
        Args:
            change: The change event from the dropdown
        """
        new_basemap_name = change['new']
        new_basemap = self.basemap_layers[new_basemap_name]
        
        # Simply change the basemap - ipyleaflet handles this correctly
        self.map.basemap = new_basemap
        self.current_basemap = new_basemap
        self.current_basemap_name = new_basemap_name
        
        with self.output:
            print(f'🗺️ Switched to {new_basemap_name} basemap')
    
    def _handle_draw(self, target, action, geo_json: Dict[str, Any]) -> None:
        """
        Handle drawing events.
        
        Args:
            target: The draw control target
            action: The action performed
            geo_json (Dict): GeoJSON representation of the drawn feature
        """
        if geo_json['geometry']['type'] in ['Polygon', 'Rectangle']:
            self._add_polygon(geo_json)
            self._update_wkt_output()
            
            with self.output:
                print(f"✅ {geo_json['geometry']['type']} drawn successfully!")
    
    def _handle_data_change(self, change) -> None:
        """
        Handle changes in the draw control data (edits and deletions).
        
        Args:
            change: The change event containing new and old data
        """
        try:
            # Update our polygon list based on current draw control data
            current_data = change['new']
            
            # Clear current polygons and rebuild from draw control data
            self.polygons.clear()
            
            # Handle different data structures
            if isinstance(current_data, dict) and 'features' in current_data:
                # GeoJSON FeatureCollection format
                features = current_data['features']
            elif isinstance(current_data, list):
                # Direct list of features
                features = current_data
            else:
                # Unknown format, skip
                return
            
            # Process each feature
            for feature in features:
                if isinstance(feature, dict) and 'geometry' in feature:
                    if feature['geometry']['type'] in ['Polygon', 'Rectangle']:
                        self._add_polygon(feature)
            
            self._update_wkt_output()
            
            with self.output:
                if len(self.polygons) == 0:
                    print('🗑️ All polygons cleared!')
                else:
                    print(f'✏️ Polygons updated! Current count: {len(self.polygons)}')
                    
        except Exception as e:
            with self.output:
                print(f'⚠️ Error handling data change: {str(e)}')
    
    def _add_polygon(self, geo_json: Dict[str, Any]) -> None:
        """
        Add a polygon to the internal storage.
        
        Args:
            geo_json (Dict): GeoJSON representation of the polygon
        """
        polygon_data = {
            'id': len(self.polygons),
            'geo_json': geo_json,
            'coordinates': geo_json['geometry']['coordinates']
        }
        self.polygons.append(polygon_data)
    
    def _coordinates_to_wkt(self, coordinates: List[List[List[float]]]) -> str:
        """
        Convert polygon coordinates to WKT format.
        
        Args:
            coordinates (List): Polygon coordinates in GeoJSON format
            
        Returns:
            str: WKT representation of the polygon
        """
        # Handle both Polygon and Rectangle geometries
        if len(coordinates) > 0 and len(coordinates[0]) > 0:
            # Get the exterior ring coordinates
            exterior_coords = coordinates[0]
            
            # Ensure the polygon is closed (first and last points are the same)
            if exterior_coords[0] != exterior_coords[-1]:
                exterior_coords.append(exterior_coords[0])
            
            # Convert to WKT format (lon lat)
            coord_strings = [f'{lon} {lat}' for lon, lat in exterior_coords]
            return f"POLYGON(({', '.join(coord_strings)}))"
        
        return ''
    
    def _update_wkt_output(self) -> None:
        """
        Update the WKT output textarea with current polygons.
        """
        if not self.polygons:
            self.wkt_output.value = ''
            return
        
        wkt_strings = []
        for i, polygon in enumerate(self.polygons):
            wkt = self._coordinates_to_wkt(polygon['coordinates'])
            if wkt:
                wkt_strings.append(f'-- Polygon {i+1} --\n{wkt}')
        
        self.wkt_output.value = '\n\n'.join(wkt_strings)
    
    def _clear_all(self, button) -> None:
        """
        Clear all drawn polygons.
        
        Args:
            button: The button widget that triggered this event
        """
        self.draw_control.clear()
        self.polygons.clear()
        self.wkt_output.value = ''
        
        with self.output:
            print('🧹 All polygons cleared!')
    
    def _copy_wkt(self, button) -> None:
        """
        Copy WKT to clipboard (display instruction).
        
        Args:
            button: The button widget that triggered this event
        """
        with self.output:
            print('📋 Select and copy the WKT text from the output area above.')
    
    def _load_wkt(self, button) -> None:
        """
        Load WKT string and display on map.
        
        Args:
            button: The button widget that triggered this event
        """
        wkt_string = self.wkt_input.value.strip()
        if not wkt_string:
            with self.output:
                print('❌ Please enter a WKT string to load.')
            return
        
        try:
            # Parse WKT string
            geometry = wkt.loads(wkt_string)
            
            if geometry.geom_type != 'Polygon':
                with self.output:
                    print(f'❌ Only Polygon geometries are supported. Got: {geometry.geom_type}')
                return
            
            # Convert to GeoJSON and add to map
            geo_json_feature = {
                'type': 'Feature',
                'geometry': mapping(geometry),
                'properties': {}
            }
            
            # Add as GeoJSON layer
            geojson_layer = GeoJSON(
                data=geo_json_feature,
                name=f'Loaded Polygon',
                style={
                    'fillColor': '#ffaa00',
                    'color': '#ff8800',
                    'fillOpacity': 0.3,
                    'weight': 2
                }
            )
            self.map.add_layer(geojson_layer)
            
            # Fit map to geometry bounds
            bounds = geometry.bounds  # (minx, miny, maxx, maxy)
            self.map.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]])
            
            with self.output:
                print(f'✅ WKT polygon loaded successfully!')
                
        except Exception as e:
            with self.output:
                print(f'❌ Error loading WKT: {str(e)}')
    
    def get_wkt_polygons(self) -> List[str]:
        """
        Get all drawn polygons as WKT strings.
        
        Returns:
            List[str]: List of WKT strings for all polygons
        """
        wkt_polygons = []
        for polygon in self.polygons:
            wkt = self._coordinates_to_wkt(polygon['coordinates'])
            if wkt:
                wkt_polygons.append(wkt)
        return wkt_polygons
    
    def display(self) -> VBox:
        """
        Display the complete polygon tool interface.
        
        Returns:
            VBox: The complete UI widget
        """
        # Instructions
        instructions = HTML(
            value="""
            <div style="background-color: #f0f8ff; padding: 10px; border-radius: 5px; margin-bottom: 10px;">
            <ul>
                <li><strong>Draw | Edit | Delete | Export | Import:</strong> WKTs</li>
            </ul>
            </div>
            """
        )
        
        # Button row
        button_row = HBox([self.clear_button, self.copy_button])
        
        # Basemap controls
        controls_section = VBox([])
        if self.show_basemap_switcher:
            controls_section.children = [
                HTML('<h4>🗺️ Map Controls</h4>'),
                self.basemap_dropdown
            ]
        
        # Load WKT section
        load_section = VBox([
            HTML('<h4>📥 Load WKT Polygon</h4>'),
            self.wkt_input,
            self.load_button
        ])
        
        # Output section
        output_section = VBox([
            HTML('<h4>📤 WKT Output</h4>'),
            self.wkt_output,
            button_row
        ])
        
        # Build the layout conditionally
        layout_children = [instructions, self.map]
        
        if self.show_basemap_switcher:
            layout_children.append(controls_section)
        
        layout_children.extend([
            load_section,
            output_section,
            HTML('<h4>📋 Messages</h4>'),
            self.output
        ])
        
        return VBox(layout_children)


def create_polygon_tool(center: tuple = (45.0, 0.0), zoom: int = 2, 
                       basemap_type: str = 'osm', 
                       show_basemap_switcher: bool = True) -> InteractivePolygonTool:
    """
    Create an interactive polygon tool with predefined configurations.
    
    Args:
        center (tuple): Initial map center coordinates (lat, lon)
        zoom (int): Initial zoom level
        basemap_type (str): Type of basemap to use:
            - 'osm': OpenStreetMap
            - 'satellite': Esri World Imagery
            - 'topo': Esri World Topo
            - 'dark': CartoDB Dark Matter
            - 'terrain': Stadia Terrain
            - 'night': NASA Earth at Night
        show_basemap_switcher (bool): Whether to show basemap switcher
    
    Returns:
        InteractivePolygonTool: Configured polygon tool instance
    """
    basemap_options = {
        'osm': basemaps.OpenStreetMap.Mapnik,
        'satellite': basemaps.Esri.WorldImagery,
        'topo': basemaps.Esri.WorldTopoMap,
        'dark': basemaps.CartoDB.DarkMatter,
        'terrain': basemaps.Stadia.StamenTerrain,
        'night': basemaps.NASAGIBS.ViirsEarthAtNight2012
    }
    
    basemap = basemap_options.get(basemap_type, basemaps.OpenStreetMap.Mapnik)
    
    return InteractivePolygonTool(
        center=center,
        zoom=zoom,
        basemap=basemap,
        show_basemap_switcher=show_basemap_switcher
    )


def search_with_polygon(polygon_tool: InteractivePolygonTool, 
                       collection_name: str = 'SENTINEL-2',
                       product_type: str = 'S2MSI1C',
                       start_date: str = '2024-01-01T00:00:00',
                       end_date: str = '2024-01-31T00:00:00',
                       cloud_cover_threshold: int = 20,
                       top: int = 10) -> Optional['pandas.DataFrame']:
    """
    Search for satellite data using drawn polygons from the polygon tool.
    
    Args:
        polygon_tool (InteractivePolygonTool): The polygon tool instance
        collection_name (str): Satellite collection name
        product_type (str): Product type to search for
        start_date (str): Start date for search
        end_date (str): End date for search
        cloud_cover_threshold (int): Maximum cloud cover percentage
        top (int): Maximum number of results
    
    Returns:
        Optional[pandas.DataFrame]: Search results or None if no polygons drawn
    """
    from phidown.search import CopernicusDataSearcher
    
    # Get WKT polygons from the tool
    wkt_polygons = polygon_tool.get_wkt_polygons()
    
    if not wkt_polygons:
        print('❌ Please draw a polygon first using the tool.')
        return None
    
    # Use the first polygon for search
    aoi_wkt = wkt_polygons[0]
    print(f'🔍 Searching with polygon: {aoi_wkt[:100]}...')
    
    try:
        # Configure search
        searcher = CopernicusDataSearcher()
        searcher._query_by_filter(
            collection_name=collection_name,
            product_type=product_type,
            orbit_direction=None,
            cloud_cover_threshold=cloud_cover_threshold,
            aoi_wkt=aoi_wkt,
            start_date=start_date,
            end_date=end_date,
            top=top
        )
        
        # Execute search
        df = searcher.execute_query()
        
        if len(df) > 0:
            print(f'✅ Found {len(df)} {collection_name} products!')
            return df
        else:
            print('❌ No products found for the specified criteria.')
            return None
            
    except Exception as e:
        print(f'❌ Error during search: {str(e)}')
        return None
