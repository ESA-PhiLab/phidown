import pytest
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from unittest.mock import patch, mock_open, MagicMock
import xml.etree.ElementTree as ET
from phidown.viz import plot_kml_coordinates, plot_product_footprints
import pandas as pd

# Define a sample KML content
SAMPLE_KML_CONTENT = """
<kml xmlns="http://www.opengis.net/kml/2.2" xmlns:gx="http://www.google.com/kml/ext/2.2">
  <Document>
    <Placemark>
      <gx:LatLonQuad>
        <coordinates>
          10,20 30,40 50,60 70,80
        </coordinates>
      </gx:LatLonQuad>
    </Placemark>
  </Document>
</kml>
"""


# Test successful plotting from KML
@patch('builtins.open', new_callable=mock_open, read_data=SAMPLE_KML_CONTENT)
@patch('xml.etree.ElementTree.parse')
@patch('folium.Map')
@patch('folium.Polygon')
def test_plot_kml_coordinates_success(mock_polygon, mock_map, mock_parse, mock_file):
    # Mock the ElementTree parsing
    mock_root = MagicMock()
    mock_coord_element = MagicMock()
    mock_coord_element.text = " 10,20 30,40 50,60 70,80 "
    mock_root.find.return_value = mock_coord_element
    mock_tree = MagicMock()
    mock_tree.getroot.return_value = mock_root
    mock_parse.return_value = mock_tree

    # Mock the folium Map and Polygon
    mock_map_instance = MagicMock()
    mock_map.return_value = mock_map_instance
    mock_polygon_instance = MagicMock()
    mock_polygon.return_value = mock_polygon_instance

    # Call the function
    result_map = plot_kml_coordinates('dummy.kml', output_html='test_map.html')

    # Assertions
    mock_parse.assert_called_once()
    mock_root.find.assert_called_once_with('.//gx:LatLonQuad/coordinates', {
        "gx": "http://www.google.com/kml/ext/2.2",
        "kml": "http://www.opengis.net/kml/2.2"
    })

    expected_coordinates = [
        [20.0, 10.0], [40.0, 30.0], [60.0, 50.0], [80.0, 70.0], [20.0, 10.0]
    ]

    mock_map.assert_called_once_with(location=[20.0, 10.0], zoom_start=10, tiles="CartoDB positron")
    mock_polygon.assert_called_once_with(
        locations=expected_coordinates,
        color="blue",
        weight=2,
        fill=True,
        fill_color="black",
        fill_opacity=0.2
    )
    mock_polygon_instance.add_to.assert_called_once_with(mock_map_instance)
    mock_map_instance.save.assert_called_once_with('test_map.html')
    assert result_map == mock_map_instance


# Test KML file not found
@patch('builtins.open', side_effect=FileNotFoundError("File not found"))
def test_plot_kml_coordinates_file_not_found(mock_file):
    with pytest.raises(FileNotFoundError):
        plot_kml_coordinates('nonexistent.kml')


# Test KML parsing error (e.g., invalid XML)
@patch('builtins.open', new_callable=mock_open, read_data="<kml><invalid></kml>")
@patch('xml.etree.ElementTree.parse', side_effect=ET.ParseError("Invalid XML"))
def test_plot_kml_coordinates_parse_error(mock_parse, mock_file):
    with pytest.raises(ET.ParseError):
        plot_kml_coordinates('invalid.kml')


# Test KML missing coordinates tag
@patch('builtins.open', new_callable=mock_open,
       read_data='<kml xmlns:gx="http://www.google.com/kml/ext/2.2"><gx:LatLonQuad></gx:LatLonQuad></kml>')
@patch('xml.etree.ElementTree.parse')
def test_plot_kml_coordinates_missing_coords(mock_parse, mock_file):
    # Mock the ElementTree parsing to return None for find
    mock_root = MagicMock()
    mock_root.find.return_value = None
    mock_tree = MagicMock()
    mock_tree.getroot.return_value = mock_root
    mock_parse.return_value = mock_tree

    with pytest.raises(AttributeError):  # Add spaces before inline comment
        plot_kml_coordinates('missing_coords.kml')


@patch('folium.Map')
@patch('folium.Polygon')
@patch('folium.GeoJson')
def test_plot_product_footprints_geography_wkt(mock_geojson, mock_polygon, mock_map):
    mock_map_instance = MagicMock()
    mock_map.return_value = mock_map_instance
    mock_geojson.return_value = MagicMock()
    mock_polygon.return_value = MagicMock()

    df = pd.DataFrame([
        {
            "Id": "x1",
            "Name": "burst-1",
            "coverage": 10.5,
            "Footprint": "geography'SRID=4326;POLYGON((12.4 41.8, 12.6 41.8, 12.6 42.0, 12.4 42.0, 12.4 41.8))'",
        }
    ])

    m = plot_product_footprints(
        df=df,
        aoi_wkt="POLYGON((12.4 41.8, 12.6 41.8, 12.6 42.0, 12.4 42.0, 12.4 41.8))",
        top_n=10,
    )

    assert m == mock_map_instance
    mock_map.assert_called_once()
    mock_polygon.assert_called_once()
    mock_geojson.assert_called_once()
    kwargs = mock_geojson.call_args.kwargs
    assert "AOI coverage" in kwargs["tooltip"]
    assert "10.50%" in kwargs["tooltip"]
    assert "popup" in kwargs


def test_plot_product_footprints_missing_columns():
    df = pd.DataFrame([{"Id": "x1"}])
    with pytest.raises(ValueError):
        plot_product_footprints(df=df, aoi_wkt=None)
