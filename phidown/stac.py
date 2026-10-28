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

import datetime
import fnmatch
import re
import time
import typing

import requests

STAC_API_URL = "https://stac.dataspace.copernicus.eu/v1"
REQUEST_TIMEOUT_SECONDS = 30
# Upper bound for one STAC page.  ``top`` larger than this is fetched over
# several pages.
MAX_PAGE_SIZE = 1000
# CDSE answers 429 when requests come too fast (for example while paging
# /collections).  Retry these with a back-off.
MAX_RATE_LIMIT_RETRIES = 6
MAX_RETRY_DELAY_SECONDS = 30

# OData attribute name -> STAC item property (names checked against CDSE
# STAC items).
ATTRIBUTE_TO_PROPERTY: typing.Dict[str, str] = {
    "productType": "product:type",
    "orbitDirection": "sat:orbit_state",
    "cloudCover": "eo:cloud_cover",
    "relativeOrbitNumber": "sat:relative_orbit",
    "orbitNumber": "sat:absolute_orbit",
    "cycleNumber": "sat:orbit_cycle",
    "platformSerialIdentifier": "platform",
    "processingLevel": "processing:level",
    "timeliness": "product:timeliness_category",
    "operationalMode": "sar:instrument_mode",
    "polarisationChannels": "sar:polarizations",
    "processorVersion": "processing:version",
    "datatakeID": "eopf:datatake_id",
    "datastripId": "eopf:datastrip_id",
    "instrumentConfigurationID": "eopf:instrument_configuration_id",
    "processingCenter": "processing:facility",
    "tileId": "grid:code",
}
PROPERTY_TO_ATTRIBUTE: typing.Dict[str, str] = {value: key for key, value in ATTRIBUTE_TO_PROPERTY.items()}

# OData $orderby field -> STAC sortby field.
ORDER_BY_TO_SORT_FIELD: typing.Dict[str, str] = {
    "ContentDate/Start": "start_datetime",
    "ContentDate/End": "end_datetime",
    "PublicationDate": "published",
    "ModificationDate": "updated",
    "OriginDate": "created",
}

# Short product types that select one STAC collection by its id suffix.
# Sentinel-3 and Sentinel-5P product types are mapped by
# :func:`product_type_slug`.  Other product types are sent as a
# ``product:type`` filter.
PRODUCT_TYPE_COLLECTION_SUFFIX: typing.Dict[str, str] = {
    "SLC": "slc",
    "GRD": "grd",
    "OCN": "ocn",
    "ETA": "etad",
    "S2MSI1C": "l1c",
    "S2MSI2A": "l2a",
}
# phidown's Sentinel-3 product type groups (config.json) -> collection id
# part.  Each group selects every collection of that instrument.
PRODUCT_TYPE_COLLECTION_FAMILY: typing.Dict[str, str] = {
    "S3OLCI": "olci",
    "S3SLSTR": "sl",
    "S3SRAL": "sr",
    "S3SYN": "syn",
}
# Collections that share a mission prefix but are not plain products of that
# mission (mosaics, bursts, calibration sets).  They are only used when named
# by a product type.
EXCLUDED_COLLECTION_MARKERS = ("global-mosaics", "slc-burst", "-gri-", "l2a-tlm", "night-time")
# Collection id suffixes that split one product type by timeliness.
TIMELINESS_SUFFIXES = ("nrt", "ntc", "stc", "nrti", "offl", "rpro")
_S3_INSTRUMENTS = {"ol": "olci", "sl": "sl", "sr": "sr", "sy": "syn"}
_S3_TIMELINESS = {"NR": "nrt", "NT": "ntc", "ST": "stc"}
# Full Sentinel-1 product types, for example IW_SLC__1S or EW_GRDM_1S.
_S1_PRODUCT_TYPE_RE = re.compile(r"^(IW|EW|SM|S[1-6]|WV)_(SLC|GRD|OCN|RAW|ETA)")
_S1_GRD_COLLECTION = "sentinel-1-grd"
# Non-Sentinel product name prefix -> collection id prefix.
_OTHER_NAME_PREFIXES = (
    ("COPERNICUS_DSM_COG_", "cop-dem-glo-"),
    ("DEM1_", "cop-dem-eea-"),
)

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

def _constellation(collections: typing.Sequence[str]) -> typing.Optional[str]:
    """Return the common ``sentinel-N`` prefix of the collections, if any."""
    prefixes = {match.group(1) for item in collections if (match := re.match(r"(sentinel-\d\w?)-", item.lower()))}
    return prefixes.pop() if len(prefixes) == 1 else None


def _property_value(name: str, value: typing.Any, constellation: typing.Optional[str] = None) -> typing.Any:
    """Convert an OData attribute value to the STAC property convention."""
    if name == "sat:orbit_state" and isinstance(value, str):
        return value.lower()
    if name == "platform" and isinstance(value, str):
        # OData uses the serial letter ("A"); STAC uses "sentinel-1a".
        if len(value) <= 2 and constellation:
            return f"{constellation}{value.lower()}"
        return value.lower()
    if name == "grid:code" and isinstance(value, str) and not value.upper().startswith("MGRS-"):
        return f"MGRS-{value.upper().lstrip('T')}"
    if name == "eopf:datatake_id" and isinstance(value, int):
        return str(value)
    return value


def _mission_collections(prefix: str, available: typing.Sequence[str]) -> typing.List[str]:
    return [item for item in available if item.lower() == prefix or item.lower().startswith(prefix + "-")]


def product_type_slug(product_type: str) -> typing.Optional[str]:
    """Return the collection id part for a product type.

    ``SLC`` -> ``slc``, ``S2MSI2A`` -> ``l2a``, ``OL_2_LFR___`` ->
    ``olci-2-lfr``, ``L2__NO2___`` -> ``l2-no2``.
    """
    upper = product_type.upper()
    if upper in PRODUCT_TYPE_COLLECTION_SUFFIX:
        return PRODUCT_TYPE_COLLECTION_SUFFIX[upper]
    tokens = [token for token in product_type.lower().split("_") if token]
    if len(tokens) < 2:
        return None
    tokens[0] = _S3_INSTRUMENTS.get(tokens[0], tokens[0])
    if tokens[0] == "l1b":
        tokens[0] = "l1"
    return "-".join(tokens)


def _collections_for_slug(prefix: str, slug: str, candidates: typing.Sequence[str]) -> typing.List[str]:
    """Return the collection named ``prefix-slug`` or its timeliness variants."""
    base = f"{prefix}-{slug}"
    # Some products have both a combined collection and timeliness
    # collections (sentinel-5p-l2-no2 and -offl/-nrti/-rpro) that cover
    # different dates, so all of them are used.  search() drops duplicates.
    return [
        item for item in candidates
        if item.lower() == base
        or (item.lower().startswith(base + "-") and item.lower()[len(base) + 1:] in TIMELINESS_SUFFIXES)
    ]


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
    candidates = _mission_collections(prefix, available)
    if not candidates:
        raise StacError(f"No STAC collection matches the collection name {collection_name!r}")
    if product_type:
        s1_match = _S1_PRODUCT_TYPE_RE.match(product_type.upper())
        if s1_match:
            # A full Sentinel-1 type selects the collection, and the
            # product:type filter keeps the mode (IW, EW, ...).
            slug = PRODUCT_TYPE_COLLECTION_SUFFIX[s1_match.group(2)]
            if s1_match.group(1) == "WV":
                slug += "-wv"
            selected = _collections_for_slug(prefix, slug, candidates)
            if selected:
                return selected, False
        family = PRODUCT_TYPE_COLLECTION_FAMILY.get(product_type.upper())
        if family:
            selected = [item for item in candidates if item.lower().startswith(f"{prefix}-{family}-")]
            if selected:
                return selected, True
        slug = product_type_slug(product_type)
        if slug:
            selected = _collections_for_slug(prefix, slug, candidates)
            if selected:
                return selected, True
    default = [item for item in candidates if not any(marker in item.lower() for marker in EXCLUDED_COLLECTION_MARKERS)]
    return default or candidates, False


def collections_for_product_name(name: str, available: typing.Sequence[str]) -> typing.List[str]:
    """Guess the STAC collections that can hold a product name (or name part).

    STAC search needs at least one collection, so name searches use this when
    the caller gives no collection.
    """
    upper = name.upper()
    s1 = re.match(r"S1[A-D_]_(\w\w)_(SLC|GRD|OCN|RAW|ETA)", upper)
    if s1:
        slug = PRODUCT_TYPE_COLLECTION_SUFFIX.get(s1.group(2), s1.group(2).lower())
        if s1.group(1) == "WV":
            slug += "-wv"
        found = _collections_for_slug("sentinel-1", slug, available)
        if found:
            return found
    s2 = re.match(r"S2[A-D_]_MSI(L1C|L2A)", upper)
    if s2:
        found = _collections_for_slug("sentinel-2", s2.group(1).lower(), available)
        if found:
            return found
    s3 = re.match(r"S3[A-D_]_(\w\w_\d_\w{6})", upper)
    if s3:
        slug = product_type_slug(s3.group(1))
        found = _collections_for_slug("sentinel-3", slug, available) if slug else []
        timeliness = re.search(r"_(NR|NT|ST)_\d{3}", upper)
        if timeliness:
            found = [item for item in found if item.lower().endswith(_S3_TIMELINESS[timeliness.group(1)])] or found
        if found:
            return found
    s5 = re.match(r"S5P_(NRTI|OFFL|RPRO)_(\w{10})", upper)
    if s5:
        slug = product_type_slug(s5.group(2))
        found = _collections_for_slug("sentinel-5p", slug, available) if slug else []
        base = f"sentinel-5p-{slug}"
        found = [item for item in found if item.lower() in (base, f"{base}-{s5.group(1).lower()}")] or found
        if found:
            return found
    for name_prefix, collection_prefix in _OTHER_NAME_PREFIXES:
        if upper.startswith(name_prefix):
            found = [item for item in available if item.lower().startswith(collection_prefix)]
            if found:
                return found
    mission = re.match(r"S([1-6])(P?)", upper)
    if mission:
        prefix = f"sentinel-{mission.group(1)}{mission.group(2).lower()}"
        if _mission_collections(prefix, available):
            return resolve_collections(prefix, None, available)[0]
    return [
        item for item in available
        if item.lower().startswith("sentinel-") and not any(marker in item.lower() for marker in EXCLUDED_COLLECTION_MARKERS)
    ]


def datetime_window_for_name(name: str) -> typing.Optional[str]:
    """Return a STAC datetime range around the first date in a product name.

    A LIKE filter on ``id`` over a large collection times out on CDSE unless
    a datetime range limits it.  Product names start with the sensing date,
    so a range of one day on each side of it is safe.
    """
    match = re.search(r"(?<!\d)(\d{4})(\d{2})(\d{2})(?:T|\d|_|$)", name)
    if not match:
        return None
    try:
        day = datetime.date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    except ValueError:
        return None
    start = day - datetime.timedelta(days=1)
    end = day + datetime.timedelta(days=2)
    return f"{start.isoformat()}T00:00:00Z/{end.isoformat()}T00:00:00Z"


def item_ids_for_name(name: str, collections: typing.Sequence[str]) -> typing.List[str]:
    """Return the STAC item ids to try for a product name.

    Item ids drop the ``.SAFE``-style extension, and Sentinel-1 GRD items
    are COG products whose ids end with ``_COG`` (the API rejects other ids
    for that collection).
    """
    stem = name
    for suffix in _PRODUCT_SUFFIXES:
        if name.upper().endswith(suffix.upper()):
            stem = name[: -len(suffix)]
            break
    # CDSE rejects ids with a .SAFE suffix, so only the stem is sent.
    if _S1_GRD_COLLECTION in collections:
        return [stem if stem.endswith("_COG") else f"{stem}_COG"]
    return [stem]


def _rfc3339(value: typing.Optional[str]) -> str:
    """Return an RFC 3339 timestamp; CDSE STAC rejects times without a zone."""
    if not value or value == "..":
        return ".."
    value = value.strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return f"{value}T00:00:00Z"
    if re.search(r"(Z|[+-]\d{2}:?\d{2})$", value, re.IGNORECASE):
        return value
    return f"{value}Z"


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
        body["datetime"] = f"{_rfc3339(start_date)}/{_rfc3339(end_date)}"

    conditions: typing.List[typing.Dict[str, typing.Any]] = []
    constellation = _constellation(collections)

    def equals(prop: str, value: typing.Any) -> None:
        if prop == "sar:polarizations" and isinstance(value, str):
            for polarization in re.split(r"[\s&+,/]+", value.upper()):
                if polarization:
                    conditions.append({"op": "a_contains", "args": [{"property": prop}, [polarization]]})
            return
        conditions.append({"op": "=", "args": [{"property": prop}, _property_value(prop, value, constellation)]})

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

def _send(http: typing.Any, method: str, url: str, **kwargs: typing.Any) -> typing.Any:
    """Send one request and retry it while the API answers 429."""
    for attempt in range(MAX_RATE_LIMIT_RETRIES + 1):
        if method == "POST":
            response = http.post(url, timeout=REQUEST_TIMEOUT_SECONDS, **kwargs)
        else:
            response = http.get(url, timeout=REQUEST_TIMEOUT_SECONDS, **kwargs)
        if getattr(response, "status_code", None) != 429 or attempt == MAX_RATE_LIMIT_RETRIES:
            return response
        retry_after = (getattr(response, "headers", None) or {}).get("Retry-After")
        try:
            delay = float(retry_after) if retry_after is not None else 2.0 ** attempt
        except ValueError:
            delay = 2.0 ** attempt
        time.sleep(min(delay, MAX_RETRY_DELAY_SECONDS))
    return response


def _rejected_filter_properties(response: typing.Any) -> typing.Set[str]:
    """Return the filter properties that a 400 FilterValidationError names."""
    if getattr(response, "status_code", None) != 400:
        return set()
    try:
        detail = response.json().get("detail", {})
    except Exception:
        return set()
    if not isinstance(detail, dict) or detail.get("code") != "FilterValidationError":
        return set()
    rejected: typing.Set[str] = set()
    for info in (detail.get("collections") or {}).values():
        if isinstance(info, dict):
            rejected.update(info.get("invalid_attributes") or [])
    return rejected


def _condition_property(condition: typing.Dict[str, typing.Any]) -> typing.Optional[str]:
    for arg in condition.get("args", []):
        if isinstance(arg, dict) and "property" in arg:
            return arg["property"]
    return None


def _split_conditions(
    filter_expr: typing.Dict[str, typing.Any],
    rejected: typing.Set[str],
) -> typing.Tuple[typing.List[typing.Dict[str, typing.Any]], typing.List[typing.Dict[str, typing.Any]]]:
    """Split a filter into server-side and client-side conditions."""
    conditions = filter_expr["args"] if filter_expr.get("op") == "and" else [filter_expr]
    server = [item for item in conditions if _condition_property(item) not in rejected]
    client = [item for item in conditions if _condition_property(item) in rejected]
    return server, client


def _combine(conditions: typing.List[typing.Dict[str, typing.Any]]) -> typing.Dict[str, typing.Any]:
    return conditions[0] if len(conditions) == 1 else {"op": "and", "args": conditions}


def _same(left: typing.Any, right: typing.Any) -> bool:
    if isinstance(left, str) or isinstance(right, str):
        return str(left).lower() == str(right).lower()
    return left == right


def _matches(item: typing.Dict[str, typing.Any], condition: typing.Dict[str, typing.Any]) -> bool:
    """Evaluate one CQL2-JSON condition (as built here) on a STAC item."""
    op = condition.get("op")
    if op == "and":
        return all(_matches(item, part) for part in condition["args"])
    name = _condition_property(condition)
    expected = condition["args"][1]
    value = item.get("id") if name == "id" else (item.get("properties") or {}).get(name)
    if value is None:
        return False
    if op == "=":
        return _same(value, expected)
    if op == "a_contains":
        values = {str(entry).lower() for entry in (value if isinstance(value, list) else [value])}
        return all(str(entry).lower() in values for entry in expected)
    if op == "like":
        pattern = expected.replace("\\%", "\0").replace("\\_", "\1").replace("%", "*").replace("_", "?")
        return fnmatch.fnmatchcase(str(value), pattern.replace("\0", "%").replace("\1", "_"))
    try:
        number, limit = float(value), float(expected)
    except (TypeError, ValueError):
        return False
    return {"<": number < limit, "<=": number <= limit, ">": number > limit, ">=": number >= limit}.get(op, False)


# base_url -> (time fetched, collection ids).  CDSE serves 400+ collections
# over 40+ pages, so the list is kept for a while per process.
_COLLECTIONS_CACHE: typing.Dict[str, typing.Tuple[float, typing.List[str]]] = {}
COLLECTIONS_CACHE_SECONDS = 3600


def list_collections(
    base_url: str = STAC_API_URL,
    session: typing.Optional[typing.Any] = None,
) -> typing.List[str]:
    """Return the ids of all collections that the STAC API serves.

    Without a ``session`` the result is cached for
    ``COLLECTIONS_CACHE_SECONDS``.
    """
    if session is None:
        cached = _COLLECTIONS_CACHE.get(base_url)
        if cached and time.monotonic() - cached[0] < COLLECTIONS_CACHE_SECONDS:
            return list(cached[1])
    http = session or requests
    url: typing.Optional[str] = f"{base_url.rstrip('/')}/collections"
    ids: typing.List[str] = []
    while url:
        response = _send(http, "GET", url)
        response.raise_for_status()
        payload = response.json()
        ids.extend(item["id"] for item in payload.get("collections", []) if "id" in item)
        url = next((link.get("href") for link in payload.get("links", []) if link.get("rel") == "next"), None)
    if session is None:
        _COLLECTIONS_CACHE[base_url] = (time.monotonic(), list(ids))
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
    # Conditions on properties that the collections do not list as
    # queryables.  CDSE rejects them, so they are checked on each item.
    client_conditions: typing.List[typing.Dict[str, typing.Any]] = []
    seen_ids: typing.Set[typing.Any] = set()
    response = None
    while True:
        response = _send(http, method, url, **({"json": request_body} if method == "POST" else {}))
        rejected = _rejected_filter_properties(response) if not items else set()
        if rejected and request_body and request_body.get("filter"):
            server_conditions, moved = _split_conditions(request_body["filter"], rejected)
            if moved:
                client_conditions.extend(moved)
                request_body = dict(request_body)
                if server_conditions:
                    request_body["filter"] = _combine(server_conditions)
                else:
                    request_body.pop("filter", None)
                    request_body.pop("filter-lang", None)
                continue
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict) or "features" not in payload:
            raise StacError("STAC search response has no 'features' list")
        if matched is None and not client_conditions:
            matched = payload.get("numberMatched", payload.get("context", {}).get("matched"))
        for item in payload["features"]:
            # The same product can be in a combined and a timeliness
            # collection; keep it once.
            if item.get("id") in seen_ids or not all(_matches(item, condition) for condition in client_conditions):
                continue
            seen_ids.add(item.get("id"))
            items.append(item)
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

def _product_s3_path(href: str, item_id: str = "") -> typing.Optional[str]:
    """Turn an asset href into the product's /eodata path used by downloaders."""
    if href.startswith("s3://"):
        path = "/" + href[len("s3://"):]
    elif href.startswith("/eodata/"):
        path = href
    else:
        return None
    segments = path.split("/")
    # Products without an extension (for example Copernicus DEM tiles) sit
    # in a folder named like the item; assets can be deeper in it.
    if item_id and item_id in segments[:-1]:
        return "/".join(segments[: segments.index(item_id) + 1])
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
    if name == "platformSerialIdentifier" and isinstance(value, str):
        match = re.match(r"sentinel-\d([a-z])$", value.lower())
        return match.group(1).upper() if match else value
    if name == "tileId" and isinstance(value, str) and value.upper().startswith("MGRS-"):
        return value[len("MGRS-"):]
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

    # The whole-product asset is "product" in some collections and
    # "Product" in others (Sentinel-1 GRD, Sentinel-2).
    product_asset = next(
        (asset for key, asset in assets.items() if key.lower() == "product" and isinstance(asset, dict)),
        None,
    )
    if product_asset:
        hrefs.insert(0, product_asset.get("href", ""))
    private = properties.get("_private") if isinstance(properties.get("_private"), dict) else {}

    odata_id = next((match.group(1) for href in hrefs if (match := _ODATA_ID_RE.search(href))), None)
    odata_id = odata_id or private.get("product_uuid")
    s3_path = next((path for href in hrefs if (path := _product_s3_path(href, item.get("id", "")))), None)
    download_url = product_asset.get("href") if product_asset else None
    content_length = product_asset.get("file:size") if product_asset else None
    if content_length is None:
        content_length = private.get("product_size")
    if content_length is None and s3_path:
        # Single-file products (Sentinel-5P .nc) have no "product" asset;
        # the asset whose href is the product itself gives the size.
        content_length = next(
            (
                asset.get("file:size") for asset in assets.values()
                if isinstance(asset, dict) and asset.get("href", "").replace("s3://", "/", 1) == s3_path
            ),
            None,
        )

    start = properties.get("start_datetime") or properties.get("datetime")
    end = properties.get("end_datetime") or properties.get("datetime")
    name = item.get("id", "")
    if private.get("product_name"):
        name = private["product_name"]
    elif s3_path:
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
    "collections_for_product_name",
    "datetime_window_for_name",
    "geojson_to_wkt",
    "item_ids_for_name",
    "item_to_record",
    "items_to_records",
    "list_collections",
    "product_type_slug",
    "resolve_collections",
    "search",
    "wkt_to_geojson",
]
