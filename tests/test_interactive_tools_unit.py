"""Unit tests for interactive helpers using fake optional modules."""

from __future__ import annotations

import importlib
import os
import sys
import types

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


class _DummyWidget:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.children = kwargs.get("children", [])
        self.value = kwargs.get("value", "")

    def on_click(self, callback):
        self._click_callback = callback

    def observe(self, callback, names=None):
        self._observe_callback = callback


class _DummyOutput(_DummyWidget):
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _DummyMap:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.basemap = kwargs.get("basemap")
        self.controls = []
        self.layers = []

    def add_control(self, control):
        self.controls.append(control)

    def add_layer(self, layer):
        self.layers.append(layer)

    def fit_bounds(self, bounds):
        self.bounds = bounds


class _DummyDrawControl(_DummyWidget):
    def clear(self):
        self.was_cleared = True

    def on_draw(self, callback):
        self._draw_callback = callback


class _DummyGeoJSON(_DummyWidget):
    pass


def _install_fake_interactive_modules():
    basemaps = types.SimpleNamespace(
        OpenStreetMap=types.SimpleNamespace(Mapnik={"name": "OSM"}),
        Esri=types.SimpleNamespace(
            WorldImagery={"name": "World Imagery"},
            WorldTopoMap={"name": "World Topo"},
            WorldStreetMap={"name": "World Street"},
            WorldTerrain={"name": "World Terrain"},
            WorldPhysical={"name": "World Physical"},
            WorldShadedRelief={"name": "World Shaded Relief"},
            NatGeoWorldMap={"name": "NatGeo"},
            OceanBasemap={"name": "Ocean"},
            WorldGrayCanvas={"name": "Gray"},
            ArcticImagery={"name": "Arctic"},
        ),
        NASAGIBS=types.SimpleNamespace(
            BlueMarble={"name": "Blue Marble"},
            ViirsEarthAtNight2012={"name": "Night"},
            ModisTerraTrueColorCR={"name": "MODIS"},
            ViirsTrueColorCR={"name": "VIIRS"},
            MEaSUREsIceVelocity3031={"name": "Ice"},
            ModisTerraLSTDay={"name": "LST"},
            ModisTerraSnowCover={"name": "Snow"},
        ),
        Stadia=types.SimpleNamespace(
            AlidadeSatellite={"name": "Satellite"},
            OSMBright={"name": "Bright"},
            AlidadeSmooth={"name": "Smooth"},
            StamenTerrain={"name": "Terrain"},
            Outdoors={"name": "Outdoors"},
            AlidadeSmoothDark={"name": "Dark"},
            StamenToner={"name": "Toner"},
            StamenWatercolor={"name": "Watercolor"},
        ),
        CartoDB=types.SimpleNamespace(
            Positron={"name": "Positron"},
            Voyager={"name": "Voyager"},
            DarkMatter={"name": "Dark Matter"},
        ),
        OpenTopoMap={"name": "OpenTopo"},
    )

    ipyleaflet = types.ModuleType("ipyleaflet")
    ipyleaflet.Map = _DummyMap
    ipyleaflet.DrawControl = _DummyDrawControl
    ipyleaflet.GeoJSON = _DummyGeoJSON
    ipyleaflet.LayersControl = _DummyWidget
    ipyleaflet.Marker = _DummyWidget
    ipyleaflet.Popup = _DummyWidget
    ipyleaflet.basemaps = basemaps

    ipywidgets = types.ModuleType("ipywidgets")
    ipywidgets.VBox = _DummyWidget
    ipywidgets.HBox = _DummyWidget
    ipywidgets.Button = _DummyWidget
    ipywidgets.Output = _DummyOutput
    ipywidgets.HTML = _DummyWidget
    ipywidgets.Textarea = _DummyWidget
    ipywidgets.Label = _DummyWidget
    ipywidgets.Layout = _DummyWidget
    ipywidgets.Dropdown = _DummyWidget

    shapely = types.ModuleType("shapely")
    shapely.geometry = types.ModuleType("shapely.geometry")
    shapely.geometry.Polygon = _DummyWidget
    shapely.geometry.mapping = lambda geometry: {"type": "Polygon", "geometry": geometry}
    shapely.wkt = types.SimpleNamespace(loads=lambda value: types.SimpleNamespace(geom_type="Polygon", bounds=(0, 0, 1, 1)))

    sys.modules["ipyleaflet"] = ipyleaflet
    sys.modules["ipywidgets"] = ipywidgets
    sys.modules["shapely"] = shapely
    sys.modules["shapely.geometry"] = shapely.geometry


def _reload_interactive_tools():
    for module_name in list(sys.modules):
        if module_name == "phidown.interactive_tools":
            sys.modules.pop(module_name)
    return importlib.import_module("phidown.interactive_tools")


def test_create_polygon_tool_uses_requested_basemap():
    _install_fake_interactive_modules()
    interactive_tools = _reload_interactive_tools()

    tool = interactive_tools.create_polygon_tool(basemap_type="satellite", show_basemap_switcher=False)

    assert tool.current_basemap == interactive_tools.basemaps.Esri.WorldImagery
    assert tool.map.basemap == interactive_tools.basemaps.Esri.WorldImagery


def test_search_with_polygon_calls_public_query_method(monkeypatch):
    _install_fake_interactive_modules()
    interactive_tools = _reload_interactive_tools()

    class FakeSearcher:
        instances = []

        def __init__(self):
            self.query_args = None
            self.__class__.instances.append(self)

        def query_by_filter(self, **kwargs):
            self.query_args = kwargs

        def execute_query(self):
            return ["ok"]

    fake_search_module = types.ModuleType("phidown.search")
    fake_search_module.CopernicusDataSearcher = FakeSearcher
    monkeypatch.setitem(sys.modules, "phidown.search", fake_search_module)

    polygon_tool = types.SimpleNamespace(
        get_wkt_polygons=lambda: ["POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))"]
    )

    result = interactive_tools.search_with_polygon(polygon_tool, collection_name="SENTINEL-2", product_type="S2MSI1C")

    assert result == ["ok"]
    assert FakeSearcher.instances[0].query_args["collection_name"] == "SENTINEL-2"
