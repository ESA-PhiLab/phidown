import argparse
import ast
import json
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional

import folium


def _coverage_to_color(value: Optional[float]) -> str:
    """Map coverage percentage (0-100) to a red-yellow-green color."""
    if value is None:
        return "#1f77b4"
    try:
        v = max(0.0, min(100.0, float(value))) / 100.0
    except (TypeError, ValueError):
        return "#1f77b4"

    # Linear blend: red -> yellow -> green
    if v < 0.5:
        r, g = 230, int(230 * (v / 0.5))
    else:
        r, g = int(230 * (1 - (v - 0.5) / 0.5)), 230
    b = 60
    return f"#{r:02x}{g:02x}{b:02x}"


def plot_kml_coordinates(kml_file: str, output_html: str = "map_overlay.html"):
    """
    Extract coordinates from a KML file and plot them on a Folium map.

    Args:
        kml_file: Path to the KML file.
        output_html: Path to save the generated HTML map.
    """
    namespace = {
        "gx": "http://www.google.com/kml/ext/2.2",
        "kml": "http://www.opengis.net/kml/2.2",
    }

    tree = ET.parse(kml_file)
    root = tree.getroot()

    coordinates_node = root.find(".//gx:LatLonQuad/coordinates", namespace)
    if coordinates_node is None or not coordinates_node.text or not coordinates_node.text.strip():
        raise ValueError("KML does not contain gx:LatLonQuad/coordinates data.")

    coordinates = []
    for coord in coordinates_node.text.split():
        parts = coord.split(",")
        if len(parts) < 2:
            raise ValueError(f"Invalid KML coordinate: {coord}")
        try:
            lon = float(parts[0])
            lat = float(parts[1])
        except ValueError as exc:
            raise ValueError(f"Invalid numeric KML coordinate: {coord}") from exc
        coordinates.append([lat, lon])

    if len(coordinates) < 3:
        raise ValueError("KML polygon requires at least three coordinate pairs.")

    coordinates.append(coordinates[0])
    m = folium.Map(location=coordinates[0], zoom_start=10, tiles="CartoDB positron")

    folium.Polygon(
        locations=coordinates,
        color="blue",
        weight=2,
        fill=True,
        fill_color="black",
        fill_opacity=0.2,
    ).add_to(m)

    m.save(output_html)
    print(f"Map has been saved as '{output_html}'. Open it in a browser to view.")
    return m


def _parse_wkt_polygon(aoi_wkt: str) -> List[List[float]]:
    """Parse POLYGON WKT into Folium coordinates: [[lat, lon], ...]."""
    if not isinstance(aoi_wkt, str) or "((" not in aoi_wkt or "))" not in aoi_wkt:
        raise ValueError("Invalid AOI WKT. Expected POLYGON WKT format.")

    coords_txt = aoi_wkt.split("((", 1)[1].split("))", 1)[0]
    coordinates: List[List[float]] = []
    for pair in coords_txt.split(","):
        parts = pair.strip().split()
        if len(parts) < 2:
            raise ValueError(f"Invalid WKT coordinate pair: {pair}")
        try:
            lon = float(parts[0])
            lat = float(parts[1])
        except ValueError as exc:
            raise ValueError(f"Invalid numeric WKT coordinate pair: {pair}") from exc
        coordinates.append([lat, lon])
    if not coordinates:
        raise ValueError("Invalid AOI WKT. Polygon has no coordinates.")
    return coordinates


def _normalize_footprint(value: Any) -> Optional[Dict[str, Any]]:
    """
    Normalize footprint values to GeoJSON dict.

    Supports:
    - GeoJSON dict
    - JSON string of GeoJSON
    - Python-literal string of dict
    - WKT POLYGON string
    - geography'SRID=4326;POLYGON(...)'
    """
    if value is None:
        return None

    try:
        import pandas as pd  # Optional runtime dependency in some environments
        if isinstance(value, float) and pd.isna(value):
            return None
    except Exception:
        pass

    if isinstance(value, dict):
        return value

    if not isinstance(value, str):
        return None

    text = value.strip()
    if not text:
        return None

    if text.startswith("{"):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            try:
                return ast.literal_eval(text)
            except Exception:
                return None

    if text.startswith("geography'SRID=4326;"):
        text = text.split(";", 1)[1].rstrip("'")

    if text.upper().startswith("POLYGON(("):
        try:
            coords_txt = text.split("((", 1)[1].split("))", 1)[0]
            ring: List[List[float]] = []
            for pair in coords_txt.split(","):
                parts = pair.strip().split()
                if len(parts) < 2:
                    return None
                ring.append([float(parts[0]), float(parts[1])])
            return {"type": "Polygon", "coordinates": [ring]}
        except (TypeError, ValueError):
            return None

    return None


def plot_product_footprints(
    df,
    aoi_wkt: Optional[str] = None,
    top_n: int = 100,
    footprint_col: Optional[str] = None,
    name_col: str = "Name",
    id_col: str = "Id",
    coverage_col: str = "coverage",
    zoom_start: int = 9,
    add_layer_control: bool = True,
    group_by: Optional[str] = "swath",
):
    """
    Plot AOI and product footprints from a search DataFrame using Folium.

    Args:
        df: Search results DataFrame (SLC or burst).
        aoi_wkt: AOI WKT polygon to overlay.
        top_n: Number of products to render.
        footprint_col: Explicit footprint column (auto-detected if None).
        name_col: Product name column for tooltip.
        id_col: Product ID column fallback for tooltip.
        coverage_col: Coverage column used to sort products before plotting.
        zoom_start: Initial map zoom level.
        add_layer_control: Add Folium layer controls for toggling overlays.
        group_by: Optional grouping layer for products ('swath', 'burst', 'product', or None).

    Returns:
        folium.Map
    """
    if df is None or len(df) == 0:
        raise ValueError("DataFrame is empty. Cannot plot footprints.")

    if footprint_col is None:
        if "GeoFootprint" in df.columns:
            footprint_col = "GeoFootprint"
        elif "Footprint" in df.columns:
            footprint_col = "Footprint"
        else:
            raise ValueError("No footprint column found. Expected 'GeoFootprint' or 'Footprint'.")

    aoi_latlon = _parse_wkt_polygon(aoi_wkt) if aoi_wkt else None

    if aoi_latlon and len(aoi_latlon) > 1:
        core = aoi_latlon[:-1]
        center_lat = sum(p[0] for p in core) / len(core)
        center_lon = sum(p[1] for p in core) / len(core)
    else:
        center_lat, center_lon = 0.0, 0.0

    m = folium.Map(location=[center_lat, center_lon], zoom_start=zoom_start, tiles="CartoDB positron")

    if aoi_latlon:
        aoi_group = folium.FeatureGroup(name="AOI", show=True)
        folium.Polygon(
            locations=aoi_latlon,
            color="black",
            weight=3,
            fill=True,
            fill_color="black",
            fill_opacity=0.08,
            tooltip="AOI",
        ).add_to(aoi_group)
        aoi_group.add_to(m)

    to_plot = df.copy()
    if coverage_col in to_plot.columns:
        to_plot = to_plot.sort_values(coverage_col, ascending=False)
    to_plot = to_plot.head(top_n)

    groups: Dict[str, folium.FeatureGroup] = {}

    def get_group(row) -> folium.FeatureGroup:
        if group_by == "swath" and "SwathIdentifier" in to_plot.columns:
            key = str(row.get("SwathIdentifier", "Unknown"))
            layer_name = f"Swath {key}"
        elif group_by == "burst" and "BurstId" in to_plot.columns:
            key = str(row.get("BurstId", "Unknown"))
            layer_name = f"Burst {key}"
        elif group_by == "product":
            product_id = row.get(id_col, "unknown")
            product_name = row.get(name_col, "") if name_col in to_plot.columns else ""
            key = str(product_id)
            layer_name = f"{product_id} | {product_name}" if product_name else str(product_id)
        else:
            key = "all"
            layer_name = "Product Footprints"
        if key not in groups:
            groups[key] = folium.FeatureGroup(name=layer_name, show=True)
            groups[key].add_to(m)
        return groups[key]

    for _, row in to_plot.iterrows():
        geojson = _normalize_footprint(row.get(footprint_col))
        if not geojson:
            continue

        label = row.get(name_col) if name_col in row else None
        if not label and id_col in row:
            label = row.get(id_col)
        if not label:
            label = "product"

        coverage_value: Optional[float] = None
        if coverage_col in row:
            raw_cov = row.get(coverage_col)
            try:
                if raw_cov is not None:
                    coverage_value = float(raw_cov)
            except (TypeError, ValueError):
                coverage_value = None

        color = _coverage_to_color(coverage_value)
        coverage_text = f"{coverage_value:.2f}%" if coverage_value is not None else "N/A"
        tooltip_text = f"{label} | AOI coverage: {coverage_text}"
        popup_text = f"Product: {label}<br>AOI coverage: {coverage_text}"

        folium.GeoJson(
            data=geojson,
            style_function=lambda _, c=color: {"color": c, "weight": 1.5, "fillOpacity": 0.08},
            tooltip=tooltip_text,
            popup=popup_text,
        ).add_to(get_group(row))

    if add_layer_control:
        folium.LayerControl(collapsed=False).add_to(m)

    return m


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Plot coordinates from a KML file on a map.")
    parser.add_argument("-kml", type=str, help="Path to the KML file.")
    parser.add_argument(
        "--output_html",
        type=str,
        default="map_overlay.html",
        help="Path to save the generated HTML map (default: map_overlay.html).",
    )

    args = parser.parse_args()
    plot_kml_coordinates(args.kml, args.output_html)
