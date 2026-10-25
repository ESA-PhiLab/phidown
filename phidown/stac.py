"""Client helpers for the Copernicus Data Space Ecosystem STAC API.

Product search in :class:`phidown.search.CopernicusDataSearcher` uses this
module.  The searcher keeps its OData-style parameters and result columns, so
this module translates in both directions:

* search parameters (collection, product type, attributes, AOI, dates,
  ordering) become a STAC ``/search`` request body with a CQL2-JSON filter;
* STAC items become rows with the columns that the rest of phidown reads
  (``Id``, ``Name``, ``S3Path``, ``ContentDate``, ``GeoFootprint``,
  ``Attributes`` ...).

Sentinel-1 burst search has no STAC equivalent and stays on OData.
"""

from __future__ import annotations

import re
import typing

import requests

STAC_API_URL = "https://stac.dataspace.copernicus.eu/v1"
REQUEST_TIMEOUT_SECONDS = 30
# Upper bound for one STAC page.  ``top`` larger than this is fetched over
# several pages.
MAX_PAGE_SIZE = 1000

# OData attribute name -> STAC item property.
ATTRIBUTE_TO_PROPERTY: typing.Dict[str, str] = {
    "productType": "product:type",
    "orbitDirection": "sat:orbit_state",
    "cloudCover": "eo:cloud_cover",
    "relativeOrbitNumber": "sat:relative_orbit",
    "orbitNumber": "sat:absolute_orbit",
    "platformSerialIdentifier": "platform",
    "processingLevel": "processing:level",
    "timeliness": "product:timeliness",
    "operationalMode": "sar:instrument_mode",
    "polarisationChannels": "sar:polarizations",
    "processorVersion": "processing:version",
    "datatakeID": "s1:datatake_id",
    "sliceNumber": "s1:slice_number",
    "totalSlices": "s1:total_slices",
    "tileId": "grid:code",
}
PROPERTY_TO_ATTRIBUTE: typing.Dict[str, str] = {value: key for key, value in ATTRIBUTE_TO_PROPERTY.items()}

# OData $orderby field -> STAC sortby field.
ORDER_BY_TO_SORT_FIELD: typing.Dict[str, str] = {
    "ContentDate/Start": "start_datetime",
    "ContentDate/End": "end_datetime",
    "PublicationDate": "published",
    "ModificationDate": "updated",
}

# Product types that select one STAC collection by its id suffix.  Other
# product types are sent as a ``product:type`` filter.
PRODUCT_TYPE_COLLECTION_SUFFIX: typing.Dict[str, str] = {
    "SLC": "slc",
    "GRD": "grd",
    "OCN": "ocn",
    "RAW": "raw",
    "S2MSI1C": "l1c",
    "S2MSI2A": "l2a",
}

_PRODUCT_SUFFIXES = (".SAFE", ".SEN3", ".SEN6", ".zip", ".nc", ".tar", ".h5", ".tif", ".TIF")
_ODATA_ID_RE = re.compile(r"Products\(([0-9a-fA-F-]{36})\)")


class StacError(RuntimeError):
    """Raised when the STAC API returns an unusable response."""


# ---------------------------------------------------------------------------
# WKT -> GeoJSON
# ---------------------------------------------------------------------------

def _split_top_level(text: str) -> typing.List[str]:
    parts: typing.List[str] = []
    depth = 0
    start = 0
    for index, char in enumerate(text):
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        elif char == "," and depth == 0:
            parts.append(text[start:index].strip())
            start = index + 1
    parts.append(text[start:].strip())
    return [part for part in parts if part]


def _strip_parens(text: str) -> str:
    text = text.strip()
    if not (text.startswith("(") and text.endswith(")")):
        raise ValueError(f"Expected a parenthesized WKT group: {text!r}")
    return text[1:-1].strip()


def _position(text: str) -> typing.List[float]:
    values = text.replace("(", " ").replace(")", " ").split()
    if len(values) < 2:
        raise ValueError(f"Invalid WKT coordinate: {text!r}")
    return [float(values[0]), float(values[1])]


def _positions(text: str) -> typing.List[typing.List[float]]:
    return [_position(part) for part in _split_top_level(_strip_parens(text))]


def wkt_to_geojson(aoi_wkt: str) -> typing.Dict[str, typing.Any]:
    """Convert a 2-D WKT geometry (EPSG:4326) to a GeoJSON geometry dict."""
    normalized = " ".join(aoi_wkt.split())
    match = re.match(r"([A-Za-z]+)\s*", normalized)
    if match is None:
        raise ValueError("WKT geometry type is missing")
    geometry_type = match.group(1).upper()
    body = normalized[match.end():]
    if geometry_type == "POINT":
        return {"type": "Point", "coordinates": _position(_strip_parens(body))}
    if geometry_type == "MULTIPOINT":
        return {"type": "MultiPoint", "coordinates": [_position(part) for part in _split_top_level(_strip_parens(body))]}
    if geometry_type == "LINESTRING":
        return {"type": "LineString", "coordinates": _positions(body)}
    if geometry_type == "MULTILINESTRING":
        return {"type": "MultiLineString", "coordinates": [_positions(part) for part in _split_top_level(_strip_parens(body))]}
    if geometry_type == "POLYGON":
        return {"type": "Polygon", "coordinates": [_positions(ring) for ring in _split_top_level(_strip_parens(body))]}
    if geometry_type == "MULTIPOLYGON":
        return {
            "type": "MultiPolygon",
            "coordinates": [
                [_positions(ring) for ring in _split_top_level(_strip_parens(polygon))]
                for polygon in _split_top_level(_strip_parens(body))
            ],
        }
    raise ValueError(f"Unsupported WKT geometry type for STAC: {geometry_type}")


def geojson_to_wkt(geometry: typing.Optional[typing.Dict[str, typing.Any]]) -> typing.Optional[str]:
    """Convert a GeoJSON Polygon/MultiPolygon to WKT, or return None."""
    if not isinstance(geometry, dict):
        return None

    def ring(points):
        return "(" + ", ".join(f"{point[0]} {point[1]}" for point in points) + ")"

    geometry_type = geometry.get("type")
    coordinates = geometry.get("coordinates")
    if geometry_type == "Polygon":
        return "POLYGON (" + ", ".join(ring(item) for item in coordinates) + ")"
    if geometry_type == "MultiPolygon":
        return "MULTIPOLYGON (" + ", ".join(
            "(" + ", ".join(ring(item) for item in polygon) + ")" for polygon in coordinates
        ) + ")"
    return None


# ---------------------------------------------------------------------------
# Request building
# ---------------------------------------------------------------------------

def _property_value(name: str, value: typing.Any) -> typing.Any:
    """Convert an OData attribute value to the STAC property convention."""
    if name in {"sat:orbit_state", "platform"} and isinstance(value, str):
        return value.lower()
    return value


def resolve_collections(
    collection_name: str,
    product_type: typing.Optional[str],
    available: typing.Sequence[str],
) -> typing.Tuple[typing.List[str], bool]:
    """Map an OData collection name and product type to STAC collection ids.

    Returns the collection ids and whether ``product_type`` is already
    expressed by the collection choice (so no ``product:type`` filter is
    needed).
    """
    prefix = collection_name.lower()
    candidates = [item for item in available if item.lower() == prefix or item.lower().startswith(prefix + "-")]
    # SENTINEL-1 must not match SENTINEL-1-RTC style collections that have
    # their own OData name.
    if candidates and prefix.count("-") == 1:
        nested = [item for item in candidates if item.lower().startswith(prefix + "-rtc")]
        candidates = [item for item in candidates if item not in nested] or candidates
    if not candidates:
        raise StacError(f"No STAC collection matches the collection name {collection_name!r}")
    if product_type:
        suffix = PRODUCT_TYPE_COLLECTION_SUFFIX.get(product_type.upper())
        if suffix:
            selected = [item for item in candidates if item.lower().endswith("-" + suffix)]
            if selected:
                return selected, True
    return candidates, False


def build_search_body(
    *,
    collections: typing.Sequence[str],
    product_type: typing.Optional[str] = None,
    orbit_direction: typing.Optional[str] = None,
    cloud_cover_threshold: typing.Optional[float] = None,
    attributes: typing.Optional[typing.Dict[str, typing.Any]] = None,
    aoi_wkt: typing.Optional[str] = None,
    start_date: typing.Optional[str] = None,
    end_date: typing.Optional[str] = None,
    limit: int = 100,
    order_by: typing.Optional[str] = None,
) -> typing.Dict[str, typing.Any]:
    """Build a STAC ``/search`` POST body from phidown search parameters."""
    body: typing.Dict[str, typing.Any] = {
        "collections": list(collections),
        "limit": int(limit),
    }
    if aoi_wkt:
        body["intersects"] = wkt_to_geojson(aoi_wkt)
    if start_date or end_date:
        body["datetime"] = f"{start_date or '..'}/{end_date or '..'}"

    conditions: typing.List[typing.Dict[str, typing.Any]] = []

    def equals(prop: str, value: typing.Any) -> None:
        if prop == "sar:polarizations" and isinstance(value, str):
            for polarization in re.split(r"[\s&+,/]+", value.upper()):
                if polarization:
                    conditions.append({"op": "a_contains", "args": [{"property": prop}, [polarization]]})
            return
        conditions.append({"op": "=", "args": [{"property": prop}, _property_value(prop, value)]})

    if product_type:
        equals("product:type", product_type)
    if orbit_direction:
        equals("sat:orbit_state", orbit_direction)
    if cloud_cover_threshold is not None:
        conditions.append({"op": "<", "args": [{"property": "eo:cloud_cover"}, cloud_cover_threshold]})
    for key, value in (attributes or {}).items():
        equals(ATTRIBUTE_TO_PROPERTY.get(key, key), value)

    if conditions:
        body["filter-lang"] = "cql2-json"
        body["filter"] = conditions[0] if len(conditions) == 1 else {"op": "and", "args": conditions}

    if order_by:
        parts = order_by.split()
        field = ORDER_BY_TO_SORT_FIELD.get(parts[0], parts[0])
        direction = parts[1].lower() if len(parts) > 1 else "asc"
        body["sortby"] = [{"field": field, "direction": direction}]
    return body


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

def list_collections(
    base_url: str = STAC_API_URL,
    session: typing.Optional[typing.Any] = None,
) -> typing.List[str]:
    """Return the ids of all collections that the STAC API serves."""
    http = session or requests
    url: typing.Optional[str] = f"{base_url.rstrip('/')}/collections"
    ids: typing.List[str] = []
    while url:
        response = http.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        payload = response.json()
        ids.extend(item["id"] for item in payload.get("collections", []) if "id" in item)
        url = next((link.get("href") for link in payload.get("links", []) if link.get("rel") == "next"), None)
    return ids


def search(
    body: typing.Dict[str, typing.Any],
    *,
    max_items: typing.Optional[int],
    base_url: str = STAC_API_URL,
    session: typing.Optional[typing.Any] = None,
) -> typing.Tuple[typing.List[typing.Dict[str, typing.Any]], typing.Optional[int], typing.Any]:
    """Run a STAC search and follow ``next`` links.

    Args:
        body: The POST body from :func:`build_search_body`.
        max_items: Stop after this many items; ``None`` fetches every page.

    Returns:
        The items, the ``numberMatched`` value when the API reports it, and
        the last HTTP response.
    """
    http = session or requests
    url = f"{base_url.rstrip('/')}/search"
    method = "POST"
    request_body: typing.Optional[typing.Dict[str, typing.Any]] = dict(body)
    items: typing.List[typing.Dict[str, typing.Any]] = []
    matched: typing.Optional[int] = None
    response = None
    while True:
        if method == "POST":
            response = http.post(url, json=request_body, timeout=REQUEST_TIMEOUT_SECONDS)
        else:
            response = http.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict) or "features" not in payload:
            raise StacError("STAC search response has no 'features' list")
        if matched is None:
            matched = payload.get("numberMatched", payload.get("context", {}).get("matched"))
        items.extend(payload["features"])
        if max_items is not None and len(items) >= max_items:
            return items[:max_items], matched, response
        next_link = next((link for link in payload.get("links", []) if link.get("rel") == "next"), None)
        if not next_link or not payload["features"]:
            return items, matched, response
        url = next_link["href"]
        method = next_link.get("method", "GET").upper()
        if method == "POST":
            # STAC paging: "merge" adds the link body to the previous body;
            # otherwise a link body replaces it.
            if next_link.get("merge", False):
                request_body = {**(request_body or {}), **next_link.get("body", {})}
            else:
                request_body = next_link.get("body", request_body)


# ---------------------------------------------------------------------------
# Item -> phidown row
# ---------------------------------------------------------------------------

def _product_s3_path(href: str) -> typing.Optional[str]:
    """Turn an asset href into the product's /eodata path used by downloaders."""
    if href.startswith("s3://"):
        path = "/" + href[len("s3://"):]
    elif href.startswith("/eodata/"):
        path = href
    else:
        return None
    segments = path.split("/")
    for index, segment in enumerate(segments):
        if segment.endswith(_PRODUCT_SUFFIXES):
            return "/".join(segments[: index + 1])
    return path.rsplit("/", 1)[0] if "." in segments[-1] else path


def _attribute_value_type(value: typing.Any) -> str:
    if isinstance(value, bool):
        return "Boolean"
    if isinstance(value, int):
        return "Integer"
    if isinstance(value, float):
        return "Double"
    if isinstance(value, str) and re.match(r"^\d{4}-\d{2}-\d{2}T", value):
        return "DateTimeOffset"
    return "String"


def _odata_attribute_value(name: str, value: typing.Any) -> typing.Any:
    if name == "orbitDirection" and isinstance(value, str):
        return value.upper()
    if name == "polarisationChannels" and isinstance(value, list):
        return "&".join(str(item) for item in value)
    return value


def item_to_record(item: typing.Dict[str, typing.Any]) -> typing.Dict[str, typing.Any]:
    """Convert one STAC item to a row with phidown's OData-style columns."""
    properties = item.get("properties", {}) or {}
    assets = item.get("assets", {}) or {}
    hrefs = [asset.get("href", "") for asset in assets.values() if isinstance(asset, dict)]
    for asset in assets.values():
        if isinstance(asset, dict):
            hrefs.extend(
                alternate.get("href", "")
                for alternate in (asset.get("alternate") or {}).values()
                if isinstance(alternate, dict)
            )

    odata_id = next((match.group(1) for href in hrefs if (match := _ODATA_ID_RE.search(href))), None)
    s3_path = next((path for href in hrefs if (path := _product_s3_path(href))), None)
    product_asset = assets.get("product") if isinstance(assets.get("product"), dict) else None
    download_url = product_asset.get("href") if product_asset else None
    content_length = product_asset.get("file:size") if product_asset else None

    start = properties.get("start_datetime") or properties.get("datetime")
    end = properties.get("end_datetime") or properties.get("datetime")
    name = item.get("id", "")
    if s3_path:
        tail = s3_path.rstrip("/").rsplit("/", 1)[-1]
        if tail.startswith(name):
            name = tail

    attributes = []
    for key, value in properties.items():
        if value is None or isinstance(value, dict):
            continue
        odata_name = PROPERTY_TO_ATTRIBUTE.get(key, key)
        odata_value = _odata_attribute_value(odata_name, value)
        if isinstance(odata_value, list):
            continue
        attributes.append(
            {
                "@odata.type": f"#OData.CSC.{_attribute_value_type(odata_value)}Attribute",
                "Name": odata_name,
                "Value": odata_value,
                "ValueType": _attribute_value_type(odata_value),
            }
        )

    return {
        "Id": odata_id or item.get("id"),
        "Name": name,
        "StacId": item.get("id"),
        "Collection": item.get("collection"),
        "ContentType": "application/octet-stream",
        "ContentLength": content_length,
        "OriginDate": properties.get("created") or start,
        "PublicationDate": properties.get("published") or properties.get("created"),
        "ModificationDate": properties.get("updated"),
        "Online": True,
        "S3Path": s3_path,
        "DownloadUrl": download_url,
        "Footprint": geojson_to_wkt(item.get("geometry")),
        "GeoFootprint": item.get("geometry"),
        "ContentDate": {"Start": start, "End": end},
        "Attributes": attributes,
        "Assets": assets,
    }


def items_to_records(items: typing.Iterable[typing.Dict[str, typing.Any]]) -> typing.List[typing.Dict[str, typing.Any]]:
    return [item_to_record(item) for item in items]


__all__ = [
    "STAC_API_URL",
    "StacError",
    "build_search_body",
    "geojson_to_wkt",
    "item_to_record",
    "items_to_records",
    "list_collections",
    "resolve_collections",
    "search",
    "wkt_to_geojson",
]
