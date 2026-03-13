import xml.etree.ElementTree as ET
import sys
import types
from unittest.mock import MagicMock, mock_open, patch

import pandas as pd
import pytest

if "folium" not in sys.modules:
    folium = types.ModuleType("folium")

    class _DummyFoliumObject:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

        def add_to(self, target):
            self.target = target
            return self

        def save(self, path):
            self.path = path

    folium.Map = _DummyFoliumObject
    folium.Polygon = _DummyFoliumObject
    folium.GeoJson = _DummyFoliumObject
    folium.FeatureGroup = _DummyFoliumObject
    folium.LayerControl = _DummyFoliumObject
    sys.modules["folium"] = folium

from phidown.viz import (
    _coverage_to_color,
    _normalize_footprint,
    _parse_wkt_polygon,
    plot_kml_coordinates,
    plot_product_footprints,
)


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


def test_coverage_to_color_handles_none_invalid_and_clamps():
    assert _coverage_to_color(None) == "#1f77b4"
    assert _coverage_to_color("bad") == "#1f77b4"
    assert _coverage_to_color(-10) == "#e6003c"
    assert _coverage_to_color(120) == "#00e63c"


def test_parse_wkt_polygon_success():
    coords = _parse_wkt_polygon("POLYGON((12.4 41.8, 12.6 41.8, 12.6 42.0, 12.4 42.0, 12.4 41.8))")

    assert coords[0] == [41.8, 12.4]
    assert coords[-1] == [41.8, 12.4]


def test_parse_wkt_polygon_rejects_bad_coordinate_pair():
    with pytest.raises(ValueError, match="Invalid WKT coordinate pair"):
        _parse_wkt_polygon("POLYGON((12.4, 12.6 41.8))")


def test_normalize_footprint_supports_multiple_formats_and_bad_wkt():
    geojson = {"type": "Polygon", "coordinates": [[[0.0, 1.0], [1.0, 1.0], [0.0, 1.0]]]}

    assert _normalize_footprint(geojson) == geojson
    assert _normalize_footprint('{"type":"Polygon","coordinates":[[[0,1],[1,1],[0,1]]]}')["type"] == "Polygon"
    assert _normalize_footprint("geography'SRID=4326;POLYGON((12.4 41.8, 12.6 41.8, 12.6 42.0, 12.4 42.0, 12.4 41.8))'")["type"] == "Polygon"
    assert _normalize_footprint("POLYGON((12.4 bad, 12.6 41.8))") is None


@patch("builtins.open", new_callable=mock_open, read_data=SAMPLE_KML_CONTENT)
@patch("xml.etree.ElementTree.parse")
@patch("folium.Map")
@patch("folium.Polygon")
def test_plot_kml_coordinates_success(mock_polygon, mock_map, mock_parse, mock_file):
    mock_root = MagicMock()
    mock_coord_element = MagicMock()
    mock_coord_element.text = " 10,20 30,40 50,60 70,80 "
    mock_root.find.return_value = mock_coord_element
    mock_tree = MagicMock()
    mock_tree.getroot.return_value = mock_root
    mock_parse.return_value = mock_tree

    mock_map_instance = MagicMock()
    mock_map.return_value = mock_map_instance
    mock_polygon_instance = MagicMock()
    mock_polygon.return_value = mock_polygon_instance

    result_map = plot_kml_coordinates("dummy.kml", output_html="test_map.html")

    expected_coordinates = [
        [20.0, 10.0],
        [40.0, 30.0],
        [60.0, 50.0],
        [80.0, 70.0],
        [20.0, 10.0],
    ]

    mock_parse.assert_called_once()
    mock_map.assert_called_once_with(location=[20.0, 10.0], zoom_start=10, tiles="CartoDB positron")
    mock_polygon.assert_called_once_with(
        locations=expected_coordinates,
        color="blue",
        weight=2,
        fill=True,
        fill_color="black",
        fill_opacity=0.2,
    )
    mock_polygon_instance.add_to.assert_called_once_with(mock_map_instance)
    mock_map_instance.save.assert_called_once_with("test_map.html")
    assert result_map == mock_map_instance


@patch("builtins.open", side_effect=FileNotFoundError("File not found"))
def test_plot_kml_coordinates_file_not_found(mock_file):
    with pytest.raises(FileNotFoundError):
        plot_kml_coordinates("nonexistent.kml")


@patch("builtins.open", new_callable=mock_open, read_data="<kml><invalid></kml>")
@patch("xml.etree.ElementTree.parse", side_effect=ET.ParseError("Invalid XML"))
def test_plot_kml_coordinates_parse_error(mock_parse, mock_file):
    with pytest.raises(ET.ParseError):
        plot_kml_coordinates("invalid.kml")


@patch(
    "builtins.open",
    new_callable=mock_open,
    read_data='<kml xmlns:gx="http://www.google.com/kml/ext/2.2"><gx:LatLonQuad></gx:LatLonQuad></kml>',
)
@patch("xml.etree.ElementTree.parse")
def test_plot_kml_coordinates_missing_coords(mock_parse, mock_file):
    mock_root = MagicMock()
    mock_root.find.return_value = None
    mock_tree = MagicMock()
    mock_tree.getroot.return_value = mock_root
    mock_parse.return_value = mock_tree

    with pytest.raises(ValueError, match="coordinates data"):
        plot_kml_coordinates("missing_coords.kml")


@patch("builtins.open", new_callable=mock_open, read_data=SAMPLE_KML_CONTENT)
@patch("xml.etree.ElementTree.parse")
def test_plot_kml_coordinates_rejects_too_few_coordinates(mock_parse, mock_file):
    mock_root = MagicMock()
    mock_coord_element = MagicMock()
    mock_coord_element.text = "10,20 30,40"
    mock_root.find.return_value = mock_coord_element
    mock_tree = MagicMock()
    mock_tree.getroot.return_value = mock_root
    mock_parse.return_value = mock_tree

    with pytest.raises(ValueError, match="at least three"):
        plot_kml_coordinates("too_few.kml")


@patch("folium.Map")
@patch("folium.Polygon")
@patch("folium.GeoJson")
def test_plot_product_footprints_geography_wkt(mock_geojson, mock_polygon, mock_map):
    mock_map_instance = MagicMock()
    mock_map.return_value = mock_map_instance
    mock_geojson.return_value = MagicMock()
    mock_polygon.return_value = MagicMock()

    df = pd.DataFrame(
        [
            {
                "Id": "x1",
                "Name": "burst-1",
                "coverage": 10.5,
                "Footprint": "geography'SRID=4326;POLYGON((12.4 41.8, 12.6 41.8, 12.6 42.0, 12.4 42.0, 12.4 41.8))'",
            }
        ]
    )

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


@patch("folium.Map")
@patch("folium.LayerControl")
@patch("folium.GeoJson")
def test_plot_product_footprints_skips_invalid_footprints(mock_geojson, mock_layer_control, mock_map):
    mock_map_instance = MagicMock()
    mock_map.return_value = mock_map_instance

    df = pd.DataFrame(
        [
            {"Id": "bad", "Name": "broken", "Footprint": "POLYGON((bad 41.8, 12.6 41.8))"},
        ]
    )

    result = plot_product_footprints(df=df, aoi_wkt=None, top_n=10)

    assert result == mock_map_instance
    mock_geojson.assert_not_called()
    mock_layer_control.assert_called_once()


def test_plot_product_footprints_missing_columns():
    df = pd.DataFrame([{"Id": "x1"}])
    with pytest.raises(ValueError):
        plot_product_footprints(df=df, aoi_wkt=None)
