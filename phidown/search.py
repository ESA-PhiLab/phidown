import requests
import pandas as pd
import numpy as np
import os
import json
import ast
import typing
import logging
from datetime import datetime, timezone
from pathlib import Path
import copy 
import asyncio
import time
import random
import re
import warnings

from .downloader import pull_down, get_token, download_burst_on_demand, TokenManager
from .download_state import DownloadStateStore, default_state_file, is_non_empty_file, is_product_complete
from .native_download import download_s3_resumable

# Optional shapely import for AOI coverage calculation
try:
    from shapely import wkt as shapely_wkt
    from shapely.geometry import shape, Polygon
    from shapely.ops import unary_union
    _SHAPELY_AVAILABLE = True
except ImportError:
    _SHAPELY_AVAILABLE = False

# Optional matplotlib import for plotting
try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    _MATPLOTLIB_AVAILABLE = True
except ImportError:
    _MATPLOTLIB_AVAILABLE = False

# Configure logging
logger = logging.getLogger(__name__)
REQUEST_TIMEOUT_SECONDS = 30
_SUPPORTED_AOI_WKT_TYPES = (
    "POINT",
    "MULTIPOINT",
    "LINESTRING",
    "MULTILINESTRING",
    "POLYGON",
    "MULTIPOLYGON",
)
_WKT_NUMBER_PATTERN = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?"
_WKT_COORDINATE_RE = re.compile(
    rf"^\s*{_WKT_NUMBER_PATTERN}\s+{_WKT_NUMBER_PATTERN}\s*$"
)


def _compute_backoff_delay(attempt_index: int, backoff_base: float, backoff_max: float) -> float:
    """Compute retry delay with exponential backoff and jitter."""
    exponential = backoff_base * (2 ** attempt_index)
    return min(backoff_max, exponential) + random.uniform(0.0, 0.5)


def _resolve_product_download_mode(mode: str = 'fast', *, resume_mode: typing.Optional[str] = None) -> str:
    if mode not in {'fast', 'safe'}:
        raise ValueError("mode must be either 'fast' or 'safe'")
    if resume_mode is None:
        return mode
    if resume_mode not in {'off', 'product'}:
        raise ValueError("resume_mode must be either 'off' or 'product'")
    warnings.warn(
        'resume_mode is deprecated; use mode="fast" or mode="safe" instead.',
        DeprecationWarning,
        stacklevel=3,
    )
    return 'safe' if resume_mode == 'product' else 'fast'


def _split_wkt_components(text: str) -> typing.List[str]:
    """Split comma-separated WKT components while respecting nested parentheses."""
    parts: typing.List[str] = []
    depth = 0
    start = 0

    for index, char in enumerate(text):
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth < 0:
                raise ValueError("unbalanced parentheses")
        elif char == "," and depth == 0:
            part = text[start:index].strip()
            if not part:
                raise ValueError("empty geometry component")
            parts.append(part)
            start = index + 1

    if depth != 0:
        raise ValueError("unbalanced parentheses")

    tail = text[start:].strip()
    if not tail:
        raise ValueError("empty geometry component")
    parts.append(tail)
    return parts


def _parse_wkt_geometry(aoi_wkt: str) -> typing.Tuple[str, str]:
    """Return the normalized WKT geometry type and body."""
    normalized_wkt = " ".join(aoi_wkt.split())
    match = re.match(r"([A-Za-z]+)", normalized_wkt)
    if match is None:
        raise ValueError("missing geometry type")

    geometry_type = match.group(1).upper()
    body = normalized_wkt[match.end():].strip()
    if not body:
        raise ValueError("missing geometry body")
    return geometry_type, body


def _unwrap_wkt_group(text: str) -> str:
    """Return the contents of a single balanced parenthesized WKT group."""
    stripped = text.strip()
    if not stripped.startswith("(") or not stripped.endswith(")"):
        raise ValueError("missing outer parentheses")

    depth = 0
    for index, char in enumerate(stripped):
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth < 0:
                raise ValueError("unbalanced parentheses")
            if depth == 0 and index != len(stripped) - 1:
                raise ValueError("unexpected trailing geometry text")

    if depth != 0:
        raise ValueError("unbalanced parentheses")

    inner = stripped[1:-1].strip()
    if not inner:
        raise ValueError("empty geometry body")
    return inner


def _parse_coordinate(text: str) -> typing.Tuple[float, float]:
    """Parse and validate a 2D WKT coordinate pair."""
    if not _WKT_COORDINATE_RE.fullmatch(text):
        raise ValueError(f"invalid coordinate pair: {text!r}")
    lon_text, lat_text = text.split()
    return float(lon_text), float(lat_text)


def _validate_coordinate(text: str) -> None:
    """Validate a 2D WKT coordinate pair."""
    _parse_coordinate(text)


def _coordinates_from_sequence(text: str) -> typing.List[typing.Tuple[float, float]]:
    """Parse a comma-separated sequence of coordinate pairs."""
    return [_parse_coordinate(component) for component in _split_wkt_components(text)]


def _validate_coordinate_sequence(text: str) -> None:
    """Validate a comma-separated sequence of 2D WKT coordinate pairs."""
    _coordinates_from_sequence(text)


def _validate_point_body(body: str) -> None:
    _validate_coordinate(_unwrap_wkt_group(body))


def _validate_linestring_body(body: str) -> None:
    _validate_coordinate_sequence(_unwrap_wkt_group(body))


def _validate_multipoint_body(body: str) -> None:
    for component in _split_wkt_components(_unwrap_wkt_group(body)):
        if component.startswith("("):
            _validate_coordinate(_unwrap_wkt_group(component))
        else:
            _validate_coordinate(component)


def _validate_multilinestring_body(body: str) -> None:
    for component in _split_wkt_components(_unwrap_wkt_group(body)):
        _validate_coordinate_sequence(_unwrap_wkt_group(component))


def _validate_polygon_ring(ring: str) -> None:
    coords = _coordinates_from_sequence(_unwrap_wkt_group(ring))
    if len(coords) < 4:
        raise ValueError("WKT polygon ring must have at least 4 coordinate pairs")
    if coords[0] != coords[-1]:
        raise ValueError("WKT polygon ring must start and end with the same point")


def _validate_polygon_body(body: str) -> None:
    for ring in _split_wkt_components(_unwrap_wkt_group(body)):
        _validate_polygon_ring(ring)


def _validate_multipolygon_body(body: str) -> None:
    for polygon in _split_wkt_components(_unwrap_wkt_group(body)):
        _validate_polygon_body(polygon)


def _validate_supported_aoi_wkt(aoi_wkt: str) -> None:
    """Validate AOI WKT syntax for the supported CDSE geometry allowlist."""
    geometry_type, body = _parse_wkt_geometry(aoi_wkt)
    if geometry_type not in _SUPPORTED_AOI_WKT_TYPES:
        supported = ", ".join(_SUPPORTED_AOI_WKT_TYPES)
        raise ValueError(
            f"Unsupported AOI WKT geometry type '{geometry_type}'. Supported types: {supported}"
        )
    if body.upper() == "EMPTY":
        return

    validators = {
        "POINT": _validate_point_body,
        "MULTIPOINT": _validate_multipoint_body,
        "LINESTRING": _validate_linestring_body,
        "MULTILINESTRING": _validate_multilinestring_body,
        "POLYGON": _validate_polygon_body,
        "MULTIPOLYGON": _validate_multipolygon_body,
    }
    validators[geometry_type](body)


def _strip_closing_coordinate(
    coords: typing.List[typing.Tuple[float, float]]
) -> typing.List[typing.Tuple[float, float]]:
    if len(coords) > 1 and coords[0] == coords[-1]:
        return coords[:-1]
    return coords


def _centroid_coordinates_from_body(
    geometry_type: str,
    body: str,
) -> typing.List[typing.Tuple[float, float]]:
    if body.upper() == "EMPTY":
        raise ValueError("AOI WKT geometry cannot be EMPTY")

    if geometry_type == "POINT":
        return [_parse_coordinate(_unwrap_wkt_group(body))]

    if geometry_type == "MULTIPOINT":
        coords: typing.List[typing.Tuple[float, float]] = []
        for component in _split_wkt_components(_unwrap_wkt_group(body)):
            if component.startswith("("):
                coords.append(_parse_coordinate(_unwrap_wkt_group(component)))
            else:
                coords.append(_parse_coordinate(component))
        return coords

    if geometry_type == "LINESTRING":
        return _coordinates_from_sequence(_unwrap_wkt_group(body))

    if geometry_type == "MULTILINESTRING":
        coords = []
        for component in _split_wkt_components(_unwrap_wkt_group(body)):
            coords.extend(_coordinates_from_sequence(_unwrap_wkt_group(component)))
        return coords

    if geometry_type == "POLYGON":
        rings = _split_wkt_components(_unwrap_wkt_group(body))
        return _strip_closing_coordinate(_coordinates_from_sequence(_unwrap_wkt_group(rings[0])))

    if geometry_type == "MULTIPOLYGON":
        coords = []
        for polygon in _split_wkt_components(_unwrap_wkt_group(body)):
            rings = _split_wkt_components(_unwrap_wkt_group(polygon))
            coords.extend(
                _strip_closing_coordinate(
                    _coordinates_from_sequence(_unwrap_wkt_group(rings[0]))
                )
            )
        return coords

    raise ValueError(f"Unsupported AOI WKT geometry type '{geometry_type}'")

# Set up S3 credentials in .s5cfg file!


############################################################################
# Copernicus Data Searcher
############################################################################
# This class allows you to search for Copernicus data using the OData API.
# It provides methods to set search parameters, build the query, execute it,
# and display the results.
# The class is initialized with default parameters, and you can customize
# the search by providing specific values for collection name, product type,
# orbit direction, cloud cover threshold, area of interest (in WKT format),
# start and end dates, maximum number of results, and order by field.
# The class also includes a method to extract valid product types from the
# configuration file based on the collection names provided.
# The search results are returned as a pandas DataFrame, and you can
# display specific columns of interest.


def _extract_date_start(value: typing.Any) -> typing.Any:
    """Extract an acquisition start datetime-like value from various representations."""
    if isinstance(value, dict):
        return value.get("Start", value)
    if isinstance(value, str):
        text = value.strip()
        if text.startswith("{") and text.endswith("}"):
            parsed: typing.Any = None
            try:
                parsed = json.loads(text)
            except Exception:
                try:
                    parsed = ast.literal_eval(text)
                except Exception:
                    parsed = None
            if isinstance(parsed, dict):
                return parsed.get("Start", value)
    return value


class CopernicusDataSearcher:
    def __init__(
        self,
        config_path: typing.Optional[str] = None,
        **query_kwargs: typing.Any
    ) -> None:
        """
        Initialize the CopernicusDataSearcher.
        Configuration is loaded from the default path.
        Call query_by_filter() to set search parameters before executing a query.
        """
        self.base_url: str = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"
        self.config: typing.Optional[dict] = self._load_config(config_path=config_path)

        # Initialize attributes to be set by query_by_filter
        self.collection_name: typing.Optional[str] = None
        self.product_type: typing.Optional[str] = None
        self.orbit_direction: typing.Optional[str] = None
        self.cloud_cover_threshold: typing.Optional[float] = None
        self.attributes: typing.Optional[typing.Dict[str, typing.Union[str, int, float]]] = None
        self.aoi_wkt: typing.Optional[str] = None
        self.start_date: typing.Optional[str] = None
        self.end_date: typing.Optional[str] = None
        
        # Burst mode parameters
        self.burst_mode: bool = False
        self.burst_id: typing.Optional[int] = None
        self.absolute_burst_id: typing.Optional[int] = None
        self.swath_identifier: typing.Optional[str] = None
        self.parent_product_name: typing.Optional[str] = None
        self.parent_product_type: typing.Optional[str] = None
        self.parent_product_id: typing.Optional[str] = None
        self.datatake_id: typing.Optional[int] = None
        self.relative_orbit_number: typing.Optional[int] = None
        self.operational_mode: typing.Optional[str] = None
        self.polarisation_channels: typing.Optional[str] = None
        self.platform_serial_identifier: typing.Optional[str] = None
        
        # Set default values for top and order_by
        self.top: int = 1000
        self.count: bool = False
        self.skip: typing.Optional[int] = None
        self.order_by: str = "ContentDate/Start desc"

        # Initialize placeholders for query results
        self._initialize_placeholders()

        # Backward-compatible constructor: allow passing query fields directly.
        if query_kwargs:
            self.query_by_filter(**query_kwargs)

    def query_by_filter(
        self,
        base_url: str = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products",
        collection_name: typing.Optional[str] = 'SENTINEL-1',
        product_type: typing.Optional[str] = None,
        orbit_direction: typing.Optional[str] = None,
        cloud_cover_threshold: typing.Optional[float] = None,
        attributes: typing.Optional[typing.Dict[str, typing.Union[str, int, float]]] = None,
        aoi_wkt: typing.Optional[str] = None,  # Coordinates should be expressed as WKT in EPSG:4326 for CDSE spatial filters.
        start_date: typing.Optional[str] = None,
        end_date: typing.Optional[str] = None,
        top: int = 1000,
        count: bool = False,
        skip: typing.Optional[int] = None,
        order_by: str = "ContentDate/Start desc",
        # Burst mode parameters
        burst_mode: bool = False,
        burst_id: typing.Optional[int] = None,
        absolute_burst_id: typing.Optional[int] = None,
        swath_identifier: typing.Optional[str] = None,
        parent_product_name: typing.Optional[str] = None,
        parent_product_type: typing.Optional[str] = None,
        parent_product_id: typing.Optional[str] = None,
        datatake_id: typing.Optional[int] = None,
        relative_orbit_number: typing.Optional[int] = None,
        operational_mode: typing.Optional[str] = None,
        polarisation_channels: typing.Optional[str] = None,
        platform_serial_identifier: typing.Optional[str] = None
    ) -> None:
        """
        Set and validate search parameters for the Copernicus data query.

        Args:
            base_url (str): The base URL for the OData API.
            collection_name (str, optional): Name of the collection to search. Defaults to 'SENTINEL-1'.
            product_type (str, optional): Type of product to filter. Defaults to None.
            orbit_direction (str, optional): Orbit direction to filter (e.g., 'ASCENDING', 'DESCENDING'). Defaults to None.
            cloud_cover_threshold (float, optional): Maximum cloud cover percentage to filter. Defaults to None.
            attributes (typing.Dict[str, typing.Union[str, int, float]], optional): Additional attributes for filtering. Defaults to None.
            aoi_wkt (str, optional): Area of Interest in WKT format. Supported types are
                POINT, MULTIPOINT, LINESTRING, MULTILINESTRING, POLYGON, and MULTIPOLYGON.
                The query builder serializes the AOI as SRID 4326 for CDSE. Defaults to None.
            start_date (str, optional): Start date for filtering (ISO 8601 format). Defaults to None.
            end_date (str, optional): End date for filtering (ISO 8601 format). Defaults to None.
            top (int, optional): Maximum number of results to retrieve. Defaults to 1000.
            count (bool, optional): Request result count and auto-fetch all pages when needed. Defaults to False.
            skip (int, optional): Number of matching results to skip for manual pagination. Defaults to None.
            order_by (str, optional): Field and direction to order results by. Defaults to "ContentDate/Start desc".
            burst_mode (bool, optional): Enable Sentinel-1 SLC Burst mode searching. Defaults to False.
            burst_id (int, optional): Burst ID to filter (burst mode only). Defaults to None.
            absolute_burst_id (int, optional): Absolute Burst ID to filter (burst mode only). Defaults to None.
            swath_identifier (str, optional): Swath identifier (e.g., 'IW1', 'IW2') (burst mode only). Defaults to None.
            parent_product_name (str, optional): Parent product name (burst mode only). Defaults to None.
            parent_product_type (str, optional): Parent product type (burst mode only). Defaults to None.
            parent_product_id (str, optional): Parent product ID (burst mode only). Defaults to None.
            datatake_id (int, optional): Datatake ID (burst mode only). Defaults to None.
            relative_orbit_number (int, optional): Relative orbit number (burst mode only). Defaults to None.
            operational_mode (str, optional): Operational mode (e.g., 'IW', 'EW') (burst mode only). Defaults to None.
            polarisation_channels (str, optional): Polarisation channels (e.g., 'VV', 'VH') (burst mode only). Defaults to None.
            platform_serial_identifier (str, optional): Platform serial identifier (e.g., 'A', 'B') (burst mode only). Defaults to None.
        """
        # Set burst mode first as it affects other validations
        self.burst_mode = burst_mode
        
        # Set base URL based on burst mode
        if self.burst_mode:
            self.base_url = "https://catalogue.dataspace.copernicus.eu/odata/v1/Bursts"
        else:
            self.base_url = base_url
            
        self.count = count  # Set or override count option
        self.skip = skip
        self._validate_skip()
        if self.count and self.skip is not None:
            raise ValueError("The 'count' and 'skip' parameters cannot be used together.")
        
        # Assign and validate parameters
        self.collection_name = collection_name
        if not self.burst_mode:
            self._validate_collection(self.collection_name) # Validate collection name only in non-burst mode

        self.product_type = product_type
        if not self.burst_mode:
            self._validate_product_type() # Validate product type (depends on collection_name and config)

        self.orbit_direction = orbit_direction
        self._validate_orbit_direction()

        self.cloud_cover_threshold = cloud_cover_threshold
        if not self.burst_mode:
            self._validate_cloud_cover_threshold()

        self.aoi_wkt = aoi_wkt
        self._validate_aoi_wkt()

        self.start_date = start_date
        self.end_date = end_date
        self._validate_time() # Validate start and end dates

        self.top = top
        self._validate_top()

        self.order_by = order_by
        self._validate_order_by()

        self.attributes = attributes
        if self.attributes is not None and not self.burst_mode:
            self._validate_attributes()
            
        # Burst-specific parameters
        if self.burst_mode:
            self.burst_id = burst_id
            self.absolute_burst_id = absolute_burst_id
            self.swath_identifier = swath_identifier
            self.parent_product_name = parent_product_name
            self.parent_product_type = parent_product_type
            self.parent_product_id = parent_product_id
            self.datatake_id = datatake_id
            self.relative_orbit_number = relative_orbit_number
            self.operational_mode = operational_mode
            self.polarisation_channels = polarisation_channels
            self.platform_serial_identifier = platform_serial_identifier
            
            # Validate burst-specific parameters
            self._validate_burst_parameters()

    # - Private Methods:
    def _load_config(self, config_path=None):
        """
        Load the configuration file.

        Args:
            config_path (str, optional): Path to the configuration file. Defaults to None.

        Raises:
            FileNotFoundError: If the configuration file is not found.
            ValueError: If the configuration file is not a valid JSON file.
        """
        if config_path is None:
            config_path = os.path.join(os.path.dirname(__file__), "config.json")

        try:
            with open(config_path, "r") as config_file:
                config: dict = json.load(config_file)
                return config
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file not found at {config_path}")
        except json.JSONDecodeError:
            raise ValueError(f"Configuration file at {config_path} is not a valid JSON file")
        except Exception as e:
            raise Exception(f"An error occurred while loading the configuration file: {e}")

    def _validate_collection(self, collection_name):
        """
        Validate the collection name against the available collections in the configuration.

        Args:
            collection_name (str): The name of the collection to validate.

        Returns:
            bool: True if the collection name is valid, False otherwise.
        """
        valid_collections = self.config.get("valid_collections", [])
        assert isinstance(valid_collections, list), "valid_collections must be a list"
        if collection_name is None:
            raise ValueError("Collection name cannot be None")
        if not isinstance(collection_name, str):
            raise TypeError("Collection name must be a string")
        if not collection_name:
            raise ValueError("Collection name cannot be empty")
        if collection_name not in valid_collections:
            raise ValueError(f"Invalid collection name: {collection_name}. Must be one of: {', '.join(valid_collections)}")

    def _get_valid_product_types(self, collection_name):
        """
        Extracts and filters valid product types from a configuration dictionary based on the given collection name.

        Args:
            collection_name (str): The name of the collection to filter the product types. (e.g., SENTINEL-1, SENTINEL-2)

        Returns:
            list: A list of valid product types for the given collection name.
        """
        product_types = {key: value.get('productType', None) for key, value in self.config['attributes'].items()}
        valid_product_types = product_types.get(collection_name, [])
        return valid_product_types or []

    def _validate_product_type(self):
        """
        Validates the provided product type against a list of valid product types.
        If the product type is None, the validation is skipped.

        Raises:
            ValueError: If the product type is not in the list of valid product types.
            TypeError: If the product type is not a string.
        """
        if self.product_type is not None:
            valid_product_types = self._get_valid_product_types(self.collection_name)
            if not isinstance(self.product_type, str):
                raise TypeError("Product type must be a string")
            if not self.product_type:
                raise ValueError("Product type cannot be empty")
            if self.product_type not in valid_product_types:
                raise ValueError(f"Invalid product type: {self.product_type}. Must be one of: {', '.join(valid_product_types)}")

    def _validate_order_by(self):
        """
        Validate the 'order_by' parameter against valid fields and directions.

        Raises:
            ValueError: If the 'order_by' parameter is invalid.
        """
        valid_order_by_fields = self.config.get("valid_order_by_fields", [])
        valid_order_by_directions = self.config.get("valid_order_by_directions", [])
        default_order_by = "ContentDate/Start desc"

        if hasattr(self, 'order_by') and self.order_by:
            parts = self.order_by.split()
            if len(parts) != 2:
                raise ValueError(
                    f"Invalid order_by format: {self.order_by}. It must be in the format 'field direction'."
                )
            field, direction = parts
            if field in valid_order_by_fields and direction in valid_order_by_directions:
                self.order_by = self.order_by
            else:
                raise ValueError(
                    f"Invalid order_by value: {self.order_by}. Must be one of: "
                    f"{', '.join([f'{f} {d}' for f in valid_order_by_fields for d in valid_order_by_directions])}"
                )
        else:
            self.order_by = default_order_by

    def _validate_top(self):
        """
        Validate the 'top' parameter to ensure it is within the allowed range.

        Raises:
            ValueError: If the 'top' parameter is not between 1 and 1000.
        """
        if not (1 <= self.top <= 1000):
            raise ValueError("The 'top' parameter must be between 1 and 1000")

    def _validate_skip(self):
        """
        Validate the 'skip' parameter to ensure it is a non-negative integer.

        Raises:
            TypeError: If the 'skip' parameter is not an integer.
            ValueError: If the 'skip' parameter is negative.
        """
        if self.skip is None:
            return
        if isinstance(self.skip, bool) or not isinstance(self.skip, int):
            raise TypeError("The 'skip' parameter must be an integer")
        if self.skip < 0:
            raise ValueError("The 'skip' parameter must be greater than or equal to 0")

    def _validate_cloud_cover_threshold(self):
        """
        Validate the 'cloud_cover_threshold' parameter to ensure it is between 0 and 100.

        Raises:
            ValueError: If the 'cloud_cover_threshold' parameter is not between 0 and 100.
        """
        if self.cloud_cover_threshold is not None and not (0 <= self.cloud_cover_threshold <= 100):
            raise ValueError("The 'cloud_cover_threshold' parameter must be between 0 and 100")

    def _validate_orbit_direction(self):
        """
        Validate the 'orbit_direction' parameter to ensure it is one of the allowed values.

        Raises:
            ValueError: If the 'orbit_direction' parameter is not 'ASCENDING', 'DESCENDING', or None.
        """
        valid_orbit_directions = ['ASCENDING', 'DESCENDING']
        if self.orbit_direction is not None and self.orbit_direction not in valid_orbit_directions:
            raise ValueError(
                f'Invalid orbit direction: {self.orbit_direction}. Must be one of: {", ".join(valid_orbit_directions)}'
            )

    def _validate_aoi_wkt(self) -> None:
        """
        Validate and normalize the 'aoi_wkt' parameter as supported WKT geometry.

        Raises:
            ValueError: If the 'aoi_wkt' parameter is malformed WKT or uses an unsupported geometry type.
            TypeError: If the 'aoi_wkt' parameter is not a string.
        """
        if self.aoi_wkt is not None:
            if not isinstance(self.aoi_wkt, str):
                raise TypeError("The 'aoi_wkt' parameter must be a string")

            self.aoi_wkt = ' '.join(self.aoi_wkt.split())

            if not self.aoi_wkt.strip():
                raise ValueError("The 'aoi_wkt' parameter cannot be empty")
            try:
                _validate_supported_aoi_wkt(self.aoi_wkt)
            except ValueError as exc:
                if str(exc).startswith("Unsupported AOI WKT geometry type"):
                    raise
                raise ValueError(f"The 'aoi_wkt' parameter must be valid WKT: {exc}") from exc

    def _validate_time(self):
        """
        Validate the 'start_date' and 'end_date' parameters to ensure they are in ISO 8601 format
        and that the start date is earlier than the end date.

        Raises:
            ValueError: If the dates are not in ISO 8601 format or if the start date is not earlier than the end date.
        """
        def normalize_iso8601(date_str: str) -> str:
            # Python 3.10's datetime.fromisoformat does not accept a trailing 'Z'.
            if date_str.endswith("Z"):
                return f"{date_str[:-1]}+00:00"
            return date_str

        def is_iso8601(date_str):
            try:
                datetime.fromisoformat(normalize_iso8601(date_str))
                return True
            except ValueError:
                return False

        def parse_iso8601(date_str: str) -> datetime:
            return datetime.fromisoformat(normalize_iso8601(date_str))

        start_dt: typing.Optional[datetime] = None
        end_dt: typing.Optional[datetime] = None
        if self.start_date:
            if not is_iso8601(self.start_date):
                raise ValueError(f"Invalid start_date format: {self.start_date}. Must be in ISO 8601 format.")
            start_dt = parse_iso8601(self.start_date)
        if self.end_date:
            if not is_iso8601(self.end_date):
                raise ValueError(f"Invalid end_date format: {self.end_date}. Must be in ISO 8601 format.")
            end_dt = parse_iso8601(self.end_date)
        if start_dt is not None and end_dt is not None:
            start_aware = start_dt.tzinfo is not None and start_dt.tzinfo.utcoffset(start_dt) is not None
            end_aware = end_dt.tzinfo is not None and end_dt.tzinfo.utcoffset(end_dt) is not None
            if start_aware != end_aware:
                raise ValueError("start_date and end_date must both be timezone-aware or both be timezone-naive.")
            if start_dt > end_dt:
                raise ValueError("start_date must not be later than end_date.")
        
        # Burst mode data availability warning
        if self.burst_mode and start_dt is not None:
            burst_availability_date = datetime.fromisoformat('2024-08-02T00:00:00')
            if start_dt.tzinfo is not None and start_dt.tzinfo.utcoffset(start_dt) is not None:
                # Compare aware datetimes in UTC.
                burst_availability_date = burst_availability_date.replace(tzinfo=timezone.utc)
                start_for_compare = start_dt.astimezone(timezone.utc)
            else:
                start_for_compare = start_dt
            if start_for_compare < burst_availability_date:
                print(f"Warning: Burst mode data is only available from August 2, 2024 onwards. "
                      f"Your start_date ({self.start_date}) is before this date. "
                      f"Results before 2024-08-02 will not be available.")

    def _validate_attributes(self):
        """
        Validate the 'attributes' parameter to ensure it is a dictionary with valid key-value pairs.

        Raises:
            TypeError: If 'attributes' is not a dictionary, or if its keys are not strings,
                    or if its values are not strings, integers, or floats.
        """
        if not isinstance(self.attributes, dict):
            raise TypeError("Attributes must be a dictionary")
        for key, value in self.attributes.items():
            if not isinstance(key, str):
                raise TypeError("Attribute keys must be strings")
            if not isinstance(value, (str, int, float)):
                raise TypeError("Attribute values must be strings, integers, or floats")

    def _validate_burst_parameters(self):
        """
        Validate burst-specific parameters.

        Raises:
            ValueError: If any burst parameter is invalid.
            TypeError: If any burst parameter has the wrong type.
        """
        # Validate swath identifier
        if self.swath_identifier is not None:
            valid_swaths = self.config.get("valid_swath_identifiers", [])
            if self.swath_identifier not in valid_swaths:
                raise ValueError(
                    f"Invalid swath_identifier: {self.swath_identifier}. "
                    f"Must be one of: {', '.join(valid_swaths)}"
                )
        
        # Validate parent product type
        if self.parent_product_type is not None:
            valid_types = self.config.get("valid_parent_product_types", [])
            if self.parent_product_type not in valid_types:
                raise ValueError(
                    f"Invalid parent_product_type: {self.parent_product_type}. "
                    f"Must be one of: {', '.join(valid_types)}"
                )
        
        # Validate operational mode
        if self.operational_mode is not None:
            valid_modes = self.config.get("valid_operational_modes", [])
            if self.operational_mode not in valid_modes:
                raise ValueError(
                    f"Invalid operational_mode: {self.operational_mode}. "
                    f"Must be one of: {', '.join(valid_modes)}"
                )
        
        # Validate polarisation channels
        if self.polarisation_channels is not None:
            valid_pols = ['VV', 'VH', 'HH', 'HV']
            if self.polarisation_channels not in valid_pols:
                raise ValueError(
                    f"Invalid polarisation_channels: {self.polarisation_channels}. "
                    f"Must be one of: {', '.join(valid_pols)}"
                )
        
        # Validate platform serial identifier
        if self.platform_serial_identifier is not None:
            valid_platforms = ['A', 'B', 'C']
            if self.platform_serial_identifier not in valid_platforms:
                raise ValueError(
                    f"Invalid platform_serial_identifier: {self.platform_serial_identifier}. "
                    f"Must be one of: {', '.join(valid_platforms)}"
                )
        
        # Validate integer parameters
        if self.burst_id is not None:
            if isinstance(self.burst_id, str):
                logger.warning("burst_id provided as string, converting to integer")
                try:
                    self.burst_id = int(self.burst_id)
                except ValueError:
                    raise TypeError("burst_id must be an integer")
            elif not isinstance(self.burst_id, int):
                raise TypeError("burst_id must be an integer")
        
        if self.absolute_burst_id is not None:
            if isinstance(self.absolute_burst_id, str):
                logger.warning("absolute_burst_id provided as string, converting to integer")
                try:
                    self.absolute_burst_id = int(self.absolute_burst_id)
                except ValueError:
                    raise TypeError("absolute_burst_id must be an integer")
            elif not isinstance(self.absolute_burst_id, int):
                raise TypeError("absolute_burst_id must be an integer")
        
        if self.datatake_id is not None:
            if isinstance(self.datatake_id, str):
                logger.warning("datatake_id provided as string, converting to integer")
                try:
                    self.datatake_id = int(self.datatake_id)
                except ValueError:
                    raise TypeError("datatake_id must be an integer")
            elif not isinstance(self.datatake_id, int):
                raise TypeError("datatake_id must be an integer")
        
        if self.relative_orbit_number is not None:
            if isinstance(self.relative_orbit_number, str):
                logger.warning("relative_orbit_number provided as string, converting to integer")
                try:
                    self.relative_orbit_number = int(self.relative_orbit_number)
                except ValueError:
                    raise TypeError("relative_orbit_number must be an integer")
            elif not isinstance(self.relative_orbit_number, int):
                raise TypeError("relative_orbit_number must be an integer")

    def _initialize_placeholders(self):
        """
        Initializes placeholder attributes for the class instance.

        This method sets up several attributes with default values of `None` to 
        serve as placeholders. These attributes include:

        - `filter_condition` (Optional[str]): A string representing a filter condition.
        - `query` (Optional[str]): A string representing the query.
        - `url` (Optional[str]): A string representing the URL.
        - `response` (Optional[requests.Response]): A `requests.Response` object for HTTP responses.
        - `json_data` (Optional[dict]): A dictionary to store JSON data from the response.
        - `df` (Optional[pd.DataFrame]): A pandas DataFrame to store tabular data.
        """
        self.filter_condition: typing.Optional[str] = None
        self.query: typing.Optional[str] = None
        self.url: typing.Optional[str] = None
        self.response: typing.Optional[requests.Response] = None
        self.json_data: typing.Optional[dict] = None
        self.df: typing.Optional[pd.DataFrame] = None

    # - Methods to build and execute the query:
    def _add_collection_filter(self, filters):
        if self.collection_name and not self.burst_mode:
            collection_filter = f"Collection/Name eq '{self.collection_name}'"
            filters.append(f"({collection_filter})")

    def _add_product_type_filter(self, filters):
        if self.product_type and not self.burst_mode:
            filters.append(
                "Attributes/OData.CSC.StringAttribute/any(att:att/Name eq 'productType' "
                f"and att/OData.CSC.StringAttribute/Value eq '{self.product_type}')"
            )

    def _add_orbit_direction_filter(self, filters):
        if self.orbit_direction:
            if self.burst_mode:
                filters.append(f"OrbitDirection eq '{self.orbit_direction}'")
            else:
                filters.append(
                    "Attributes/OData.CSC.StringAttribute/any(att:att/Name eq 'orbitDirection' "
                    f"and att/OData.CSC.StringAttribute/Value eq '{self.orbit_direction}')"
                )

    def _add_cloud_cover_filter(self, filters):
        if self.cloud_cover_threshold is not None and not self.burst_mode:
            filters.append(
                "Attributes/OData.CSC.DoubleAttribute/any(att:att/Name eq 'cloudCover' "
                f"and att/OData.CSC.DoubleAttribute/Value lt {self.cloud_cover_threshold})"
            )

    def _add_aoi_filter(self, filters):
        if self.aoi_wkt:
            filters.append(f"OData.CSC.Intersects(area=geography'SRID=4326;{self.aoi_wkt}')")

    def _add_date_filters(self, filters):
        if self.start_date:
            if self.burst_mode:
                filters.append(f"ContentDate/Start ge {self.start_date}")
            else:
                filters.append(f"ContentDate/Start ge {self.start_date}")
        if self.end_date:
            if self.burst_mode:
                filters.append(f"ContentDate/Start le {self.end_date}")
            else:
                filters.append(f"ContentDate/Start lt {self.end_date}")

    def _add_attribute_filters(self, filters):
        if self.attributes and not self.burst_mode:
            for key, value in self.attributes.items():
                if isinstance(value, str):
                    filters.append(
                        f"Attributes/OData.CSC.StringAttribute/any(att:att/Name eq '{key}' "
                        f"and att/OData.CSC.StringAttribute/Value eq '{value}')"
                    )
                elif isinstance(value, int):
                    filters.append(
                        f"Attributes/OData.CSC.IntegerAttribute/any(att:att/Name eq '{key}' "
                        f"and att/OData.CSC.IntegerAttribute/Value eq {value})"
                    )
                elif isinstance(value, float):
                    filters.append(
                        f"Attributes/OData.CSC.DoubleAttribute/any(att:att/Name eq '{key}' "
                        f"and att/OData.CSC.DoubleAttribute/Value eq {value})"
                    )
                else:
                    raise TypeError(f"Unsupported attribute type for {key}: {type(value)}")

    def _add_burst_filters(self, filters):
        """Add burst-specific filters when in burst mode."""
        if not self.burst_mode:
            return
        
        # Burst ID
        if self.burst_id is not None:
            filters.append(f"BurstId eq {self.burst_id}")
        
        # Absolute Burst ID
        if self.absolute_burst_id is not None:
            filters.append(f"AbsoluteBurstId eq {self.absolute_burst_id}")
        
        # Swath Identifier
        if self.swath_identifier is not None:
            filters.append(f"SwathIdentifier eq '{self.swath_identifier}'")
        
        # Parent Product Name
        if self.parent_product_name is not None:
            filters.append(f"ParentProductName eq '{self.parent_product_name}'")
        
        # Parent Product Type
        if self.parent_product_type is not None:
            filters.append(f"ParentProductType eq '{self.parent_product_type}'")
        
        # Parent Product ID
        if self.parent_product_id is not None:
            filters.append(f"ParentProductId eq '{self.parent_product_id}'")
        
        # Datatake ID
        if self.datatake_id is not None:
            filters.append(f"DatatakeID eq {self.datatake_id}")
        
        # Relative Orbit Number
        if self.relative_orbit_number is not None:
            filters.append(f"RelativeOrbitNumber eq {self.relative_orbit_number}")
        
        # Operational Mode
        if self.operational_mode is not None:
            filters.append(f"OperationalMode eq '{self.operational_mode}'")
        
        # Polarisation Channels
        if self.polarisation_channels is not None:
            filters.append(f"PolarisationChannels eq '{self.polarisation_channels}'")
        
        # Platform Serial Identifier
        if self.platform_serial_identifier is not None:
            filters.append(f"PlatformSerialIdentifier eq '{self.platform_serial_identifier}'")

    def _build_filter(self):
        """
        Build the OData filter condition based on the provided parameters.
        """
        filters = []
        self._add_collection_filter(filters)
        self._add_product_type_filter(filters)
        self._add_orbit_direction_filter(filters)
        self._add_cloud_cover_filter(filters)
        self._add_aoi_filter(filters)
        self._add_date_filters(filters)
        self._add_attribute_filters(filters)
        self._add_burst_filters(filters)

        # Combine all filters into a single filter condition
        if not filters:
            raise ValueError("No valid filters provided. At least one filter is required.")

        self.filter_condition = " and ".join(filters)

    def _build_query(self, skip: typing.Optional[int] = None):
        """Build the full OData query URL"""
        self._build_filter()
        self.query = f"?$filter={self.filter_condition}&$orderby={self.order_by}&$top={self.top}"

        effective_skip = self.skip if skip is None else skip
        if effective_skip is not None:
            self.query += f"&$skip={effective_skip}"
        
        # Add $expand=Attributes only for non-burst mode
        if not self.burst_mode:
            self.query += "&$expand=Attributes"
            
        if self.count:
            self.query += "&$count=true"
            
        self.url = f"{self.base_url}{self.query}"
        return self.url

    def execute_query(self):
        """Execute the query and retrieve data.
        
        If count=True and the total number of results exceeds the 'top' limit,
        this method will automatically paginate through all results using
        multiple requests with the $skip parameter, combining all results
        into a single DataFrame.
        
        The returned DataFrame includes a 'coverage' column showing the percentage
        (0-100) of the AOI covered by each product's footprint, if aoi_wkt is set
        and shapely is available.
        
        Returns:
            pd.DataFrame: DataFrame containing all retrieved products with coverage column.
        """
        url = self._build_query()
        self.response = copy.deepcopy(requests.get(url, timeout=REQUEST_TIMEOUT_SECONDS))
        self.response.raise_for_status()  # Raise an error for bad status codes

        self.json_data = self.response.json()
        self.num_results = self.json_data.get('@odata.count', 0)
        
        # Check if pagination is needed
        if self.count and self.num_results > self.top:
            self._execute_paginated_query()
        else:
            self.df = pd.DataFrame.from_dict(self.json_data['value'])
        
        # Add coverage column if AOI is set
        self._add_coverage_column()
        
        return self.df

    def _execute_paginated_query(self):
        """Execute paginated queries when results exceed top limit using asyncio"""
        all_data = []
        
        # Add first page (already retrieved in execute_query)
        if 'value' in self.json_data:
            all_data.extend(self.json_data['value'])
            
        page_size = self.top  # Use the current top value as page size
        
        # Burst API has a hard limit on $skip (around 10,000 results max)
        # We must respect this limit to avoid 422 errors
        max_skip = self.num_results
        if self.burst_mode:
            burst_max_results = 10000
            if self.num_results > burst_max_results:
                print(f"Warning: Burst API limits pagination to ~{burst_max_results} results. "
                      f"Only retrieving first {burst_max_results} of {self.num_results} available results.")
                max_skip = burst_max_results
        
        # Calculate skips based on total results and page size
        skips = range(page_size, max_skip, page_size)
        
        if not skips:
            self.df = pd.DataFrame.from_dict(all_data)
            return self.df

        urls = []
        for skip in skips:
            urls.append(self._build_query(skip=skip))
            
        async def fetch_url(url):
            loop = asyncio.get_running_loop()
            try:
                response = await loop.run_in_executor(
                    None, lambda: requests.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
                )
                response.raise_for_status()
                return response.json()
            except Exception as e:
                return e

        async def fetch_all(urls):
            tasks = [fetch_url(url) for url in urls]
            return await asyncio.gather(*tasks, return_exceptions=True)

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # If in a running loop (e.g. Jupyter), run the new loop in a separate thread
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                results = pool.submit(asyncio.run, fetch_all(urls)).result()
        else:
            results = asyncio.run(fetch_all(urls))

        # Process results
        for res in results:
            if isinstance(res, Exception):
                print(f"Warning: Error retrieving page: {res}")
            elif isinstance(res, dict) and 'value' in res:
                all_data.extend(res['value'])
        
        # Create DataFrame from all collected data
        self.df = pd.DataFrame.from_dict(all_data)

    # -------------------------------------------------------------------------
    # AOI Coverage Calculation Methods
    # -------------------------------------------------------------------------
    
    def _calculate_aoi_coverage(self, footprint: typing.Any) -> typing.Optional[float]:
        """Calculate the coverage percentage of AOI by a product footprint.
        
        Args:
            footprint: Product footprint as GeoJSON dict, GeoJSON string, or WKT string.
            
        Returns:
            float: Coverage percentage (0-100) or None if calculation fails.
        """
        if not _SHAPELY_AVAILABLE:
            return None
        
        if self.aoi_wkt is None:
            return None
        
        try:
            # Parse AOI
            aoi_geom = shapely_wkt.loads(self.aoi_wkt)
            
            # Parse footprint
            if footprint is None:
                return None
            
            if isinstance(footprint, str):
                if footprint.strip().startswith('{'):
                    # GeoJSON string
                    fp_geom = shape(json.loads(footprint))
                else:
                    # WKT string
                    fp_geom = shapely_wkt.loads(footprint)
            elif isinstance(footprint, dict):
                # GeoJSON dict
                fp_geom = shape(footprint)
            else:
                return None
            
            # Calculate intersection
            if not aoi_geom.is_valid or not fp_geom.is_valid:
                return None
            
            intersection = aoi_geom.intersection(fp_geom)
            
            if aoi_geom.area > 0:
                coverage_pct = (intersection.area / aoi_geom.area) * 100
                return min(100.0, round(coverage_pct, 2))
            return 0.0
            
        except Exception as e:
            logger.debug(f"Could not calculate coverage: {e}")
            return None
    
    def _add_coverage_column(self) -> None:
        """Add coverage column to the results DataFrame.
        
        The coverage column shows the percentage (0-100) of the AOI covered
        by each product's footprint. Requires shapely to be installed.
        """
        if self.df is None or self.df.empty:
            return
        
        if self.aoi_wkt is None:
            # No AOI set, skip coverage calculation
            print("Warning: No AOI (aoi_wkt) provided. Coverage calculation requires an AOI to measure against.")
            self.df['coverage'] = None
            return
        
        if not _SHAPELY_AVAILABLE:
            logger.warning("shapely not installed. Coverage calculation disabled. "
                          "Install with: pip install shapely")
            self.df['coverage'] = None
            return
        
        # Determine footprint column based on mode
        # For bursts, prefer GeoFootprint (GeoJSON dict) over Footprint (non-standard WKT)
        # Burst 'Footprint' format is: geography'SRID=4326;POLYGON(...)' which needs parsing
        if self.burst_mode:
            # Prefer GeoFootprint (clean GeoJSON) for bursts
            footprint_col = 'GeoFootprint' if 'GeoFootprint' in self.df.columns else 'Footprint'
        else:
            footprint_col = 'GeoFootprint'
        
        if footprint_col not in self.df.columns:
            logger.warning(f"Footprint column '{footprint_col}' not found in results. "
                          "Coverage calculation skipped.")
            self.df['coverage'] = None
            return
        
        # Calculate coverage for each product
        self.df['coverage'] = self.df[footprint_col].apply(self._calculate_aoi_coverage)

    def query_by_name(self, product_name: str) -> pd.DataFrame:
        """
        Query Copernicus data by a specific product name.
        The results (DataFrame) are stored in self.df.

        Args:
            product_name (str): The exact name of the product to search for.

        Returns:
            pd.DataFrame: A DataFrame containing the product details.
                          Returns an empty DataFrame if the product is not found or an error occurs.
        
        Raises:
            ValueError: If product_name is empty or not a string.
        """
        if not product_name or not isinstance(product_name, str):
            raise ValueError("Product name must be a non-empty string.")

        # Initialize placeholders to ensure a clean state for this specific query type
        self._initialize_placeholders()

        # Construct the query URL, including $expand=Attributes for consistency
        self.url = f"{self.base_url}?$filter=Name eq '{product_name}'&$expand=Attributes"
        
        try:
            self.response = requests.get(self.url, timeout=REQUEST_TIMEOUT_SECONDS)
            self.response.raise_for_status()  # Raise an error for bad status codes (4xx or 5xx)

            self.json_data = self.response.json()
            
            if 'value' in self.json_data:
                self.df = pd.DataFrame.from_dict(self.json_data['value'])
            else:
                print(f"Warning: 'value' field not found in response for product name query: {product_name}")
                self.df = pd.DataFrame()

        except requests.exceptions.HTTPError as http_err:
            print(f"HTTP error occurred while querying by name '{product_name}': {http_err} (URL: {self.url})")
            if self.response is not None and self.response.status_code == 404:
                print(f"Product '{product_name}' not found (404).")
            self.df = pd.DataFrame() 
            # Optionally re-raise for non-404 errors if stricter error handling is needed
            # if self.response is None or self.response.status_code != 404:
            #     raise
        except json.JSONDecodeError as json_err:
            print(f"JSON decode error while querying by name '{product_name}': {json_err} (URL: {self.url})")
            self.df = pd.DataFrame()
        except Exception as e:
            print(f"An unexpected error occurred while querying by name '{product_name}': {e} (URL: {self.url})")
            self.df = pd.DataFrame()
            # Optionally re-raise 
            # raise

        return self.df

    def search_products_by_name_pattern(
        self,
        name_pattern: str,
        match_type: str,
        collection_name_filter: typing.Optional[str] = None,
        top: typing.Optional[int] = None,
        order_by: typing.Optional[str] = None
    ) -> pd.DataFrame:
        """
        Searches for Copernicus products by a name pattern using 'exact', 'contains', 'startswith', or 'endswith'.
        Optionally filters by a specific collection name or uses the instance's current collection if set.
        The results (DataFrame) are stored in self.df.

        Args:
            name_pattern (str): The pattern to search for in the product name.
            match_type (str): The type of match. Must be one of 'exact', 'contains', 'startswith', 'endswith'.
            collection_name_filter (str, optional): Specific collection to filter this search by.
                                                If None, and self.collection_name (instance attribute) is set,
                                                self.collection_name will be used. If both are None, no collection
                                                filter based on collection name is applied for this specific search.
            top (int, optional): Maximum number of results. If None, uses self.top (instance default).
                                 Must be between 1 and 1000.
            order_by (str, optional): Field and direction to order results (e.g., 'ContentDate/Start desc').
                                      If None, uses self.order_by (instance default).

        Returns:
            pd.DataFrame: DataFrame with product details. Empty if no match or error.

        Raises:
            ValueError: If name_pattern is empty, match_type is invalid, or effective 'top' is out of range.
                        Also if 'collection_name_filter' is provided and is invalid.
        """
        if not name_pattern or not isinstance(name_pattern, str):
            raise ValueError("Name pattern must be a non-empty string.")

        valid_match_types = ['exact', 'contains', 'startswith', 'endswith']
        if match_type not in valid_match_types:
            raise ValueError(f"Invalid match_type: {match_type}. Must be one of: {', '.join(valid_match_types)}")

        self._initialize_placeholders()  # Reset previous results

        filters = []

        # 1. Name filter based on match_type
        if match_type == 'exact':
            name_filter_str = f"Name eq '{name_pattern}'"
        elif match_type == 'contains':
            name_filter_str = f"contains(Name,'{name_pattern}')"
        elif match_type == 'startswith':
            name_filter_str = f"startswith(Name,'{name_pattern}')"
        elif match_type == 'endswith':
            name_filter_str = f"endswith(Name,'{name_pattern}')"
        filters.append(name_filter_str)

        # 2. Collection filter
        final_collection_name_to_use = None
        if collection_name_filter:
            try:
                # Validate the explicitly passed collection name
                self._validate_collection(collection_name_filter)
                final_collection_name_to_use = collection_name_filter
            except ValueError as e:
                raise ValueError(f"Invalid 'collection_name_filter' provided: '{collection_name_filter}'. Validation error: {e}")
        elif self.collection_name: # If no specific collection is passed, use instance's collection_name if set
            final_collection_name_to_use = self.collection_name

        if final_collection_name_to_use:
            filters.append(f"Collection/Name eq '{final_collection_name_to_use}'")

        filter_condition = " and ".join(filters)

        # Determine effective top and order_by values
        query_top = top if top is not None else self.top
        query_order_by = order_by if order_by is not None else self.order_by

        # Validate effective top value
        if not (1 <= query_top <= 1000):
            raise ValueError(f"The 'top' parameter for the query must be between 1 and 1000. Effective value: {query_top}")
        
        # Note: query_order_by uses instance default or passed argument.
        # self.order_by is validated when set by _query_by_filter.
        # If query_order_by is passed as an argument, its format is trusted here.

        self.query = f"?$filter={filter_condition}&$orderby={query_order_by}&$top={query_top}&$expand=Attributes"
        self.url = f"{self.base_url}{self.query}"

        try:
            self.response = requests.get(self.url, timeout=REQUEST_TIMEOUT_SECONDS)
            self.response.raise_for_status()
            self.json_data = self.response.json()

            if 'value' in self.json_data:
                self.df = pd.DataFrame.from_dict(self.json_data['value'])
            else:
                print(f"Warning: 'value' field not found in response for name pattern query: '{name_pattern}', type: '{match_type}'")
                self.df = pd.DataFrame()

        except requests.exceptions.HTTPError as http_err:
            print(f"HTTP error for name pattern '{name_pattern}' ({match_type}): {http_err} (URL: {self.url})")
            if self.response is not None and self.response.status_code == 404:
                print(f"No products found matching pattern '{name_pattern}' ({match_type}) with current filters.")
            self.df = pd.DataFrame()
        except json.JSONDecodeError as json_err:
            print(f"JSON decode error for name pattern '{name_pattern}' ({match_type}): {json_err} (URL: {self.url})")
            self.df = pd.DataFrame()
        except Exception as e:
            print(f"Unexpected error for name pattern '{name_pattern}' ({match_type}): {e} (URL: {self.url})")
            self.df = pd.DataFrame()

        return self.df

    def display_results(self, columns=None, top_n=10):
        """Display the query results with selected columns"""
        if self.df is None:
            self.execute_query()

        if columns is None:
            # Use different default columns for burst mode vs product mode
            if self.burst_mode:
                columns = ['Id','coverage','BurstId', 'SwathIdentifier', 'ParentProductName', 
                          'PolarisationChannels', 'OrbitDirection', 'ContentDate']
            else:
                columns = ['Id', 'coverage', 'Name', 'S3Path', 'GeoFootprint', 'OriginDate', 'Attributes']

        if 'OriginDate' in self.df.columns:
            self.df['OriginDate'] = pd.to_datetime(self.df['OriginDate']).dt.strftime('%Y-%m-%d %H:%M:%S')

        if not isinstance(columns, list):
            raise TypeError("Columns must be a list of strings")

        if self.df.empty:
            print("The DataFrame is empty.")
            return None
        else:
            # Only show columns that exist in the DataFrame
            available_columns = [col for col in columns if col in self.df.columns]
            return self.df[available_columns].head(top_n)

    def download_product(self, eo_product_name: str, 
                        output_dir: str, 
                        config_file = '.s5cfg',
                        mode: str = 'fast',
                        verbose=True,
                        show_progress=True,
                        retry_count: int = 1,
                        connect_timeout: float = 30.0,
                        read_timeout: typing.Optional[float] = None,
                        state_file: typing.Optional[str] = None,
                        s5cmd_retry_count: typing.Optional[int] = None,
                        max_workers: typing.Optional[int] = None,
                        backoff_base: float = 2.0,
                        backoff_max: float = 60.0,
                        reset_config: bool = False):
        """
        Download the EO product using the downloader module.
        
        Args:
            eo_product_name: Name of the EO product to download
            output_dir: Local output directory for downloaded files
            config_file: Path to s5cmd configuration file
            mode: Download mode ('fast' for s5cmd, 'safe' for resumable native downloads)
            verbose: Whether to print download information
            show_progress: Whether to show tqdm progress bar during download
            retry_count: Number of command-level retry attempts
            connect_timeout: Network connection timeout in seconds for native transfers
            read_timeout: Network read timeout in seconds for native transfers
            state_file: Optional JSON state file path for resumable runs
            s5cmd_retry_count: Optional internal retry count for s5cmd
            max_workers: Optional worker count for s5cmd
            backoff_base: Base delay in seconds for retry backoff
            backoff_max: Max delay in seconds for retry backoff
            reset_config: Whether to reset configuration and prompt for credentials
        
        Returns:
            bool: True if download was successful, False otherwise
        """
        if mode not in {'fast', 'safe'}:
            raise ValueError("mode must be either 'fast' or 'safe'")
            
        res = self.query_by_name(eo_product_name)
        if res.empty:
            print(f"No product found with name: {eo_product_name}")
            return False
        
        # file size in bytes
        content_length = res['ContentLength'].iloc[0]
        
        # Ensure output_dir is an absolute path
        abs_output_dir = os.path.abspath(output_dir)

        if verbose:
            print(f"Downloading product: {eo_product_name}")
            print(f"Output directory: {abs_output_dir}")
            print(f"Mode: {mode}")
        
        s3path = res['S3Path'].iloc[0]
        
        # Choose download method based on mode
        if mode == 'safe':
            # Use resumable native download with command-level retries.
            attempts = max(1, int(retry_count))
            should_reset_config = reset_config
            last_error = None

            for attempt in range(attempts):
                try:
                    result = download_s3_resumable(
                        s3_path=s3path,
                        output_dir=abs_output_dir,
                        config_file=config_file,
                        download_all=True,
                        state_file=state_file,
                        state_item_id=f'name:{eo_product_name}',
                        connect_timeout=connect_timeout,
                        read_timeout=read_timeout,
                        show_progress=show_progress,
                        attempts=attempt + 1,
                        persist_state=True,
                        reset_config=should_reset_config,
                    )
                    return result.status in ('downloaded', 'skipped')
                except Exception as exc:
                    last_error = str(exc)
                    should_reset_config = False
                    if attempt < attempts - 1:
                        delay = _compute_backoff_delay(
                            attempt,
                            backoff_base=backoff_base,
                            backoff_max=backoff_max,
                        )
                        if verbose:
                            print(
                                f"Safe download attempt {attempt + 1}/{attempts} failed "
                                f"({exc}). Retrying in {delay:.1f}s..."
                            )
                        time.sleep(delay)

            if verbose and last_error is not None:
                print(f"Safe download failed after {attempts} attempts: {last_error}")
            return False
        else:
            # Use fast s5cmd download
            success = pull_down(
                s3_path=s3path,
                output_dir=abs_output_dir,
                config_file=config_file,
                total_size=content_length,
                show_progress=show_progress,
                retry_count=retry_count,
                s5cmd_retry_count=s5cmd_retry_count,
                max_workers=max_workers,
                backoff_base=backoff_base,
                backoff_max=backoff_max,
                reset=reset_config,
            )
            return success
    # -------------------------------------------------------------------------
    # Orbit Optimization Methods
    # -------------------------------------------------------------------------
    
    # Regional longitude bounds for orbit direction preferences
    _EUROPE_AMERICA_LON_BOUNDS = (-180, 60)  # Descending preferred
    _ASIA_AUSTRALIA_LON_BOUNDS = (60, 180)   # Ascending preferred
    
    # Subswath priority order (lower index = higher priority)
    _SUBSWATH_PRIORITY = {'IW1': 0, 'IW2': 1, 'IW3': 2}
    
    def _get_aoi_centroid(self, aoi_wkt: typing.Optional[str] = None) -> typing.Tuple[float, float]:
        """Calculate the centroid of the AOI.
        
        Args:
            aoi_wkt: Supported AOI WKT geometry used for centroid-based orbit heuristics.
                Uses self.aoi_wkt if None.
        
        Returns:
            Tuple[float, float]: (longitude, latitude) of the centroid.
            
        Raises:
            ValueError: If AOI is not set or cannot be parsed.
        """
        wkt = aoi_wkt or self.aoi_wkt
        if wkt is None:
            raise ValueError("AOI WKT is not set")

        try:
            normalized_wkt = " ".join(wkt.split())
            _validate_supported_aoi_wkt(normalized_wkt)
            geometry_type, body = _parse_wkt_geometry(normalized_wkt)
            coords = _centroid_coordinates_from_body(geometry_type, body)

            if not coords:
                raise ValueError("Could not parse AOI coordinates")

            lon_avg = sum(c[0] for c in coords) / len(coords)
            lat_avg = sum(c[1] for c in coords) / len(coords)
            return lon_avg, lat_avg
        except ValueError as e:
            raise ValueError(f"Could not parse AOI WKT: {e}")
    
    def _get_recommended_orbit_direction(self, aoi_wkt: typing.Optional[str] = None) -> str:
        """Determine recommended orbit direction based on AOI location.
        
        For Europe/America (longitude -180 to 60): Descending preferred
        For Asia/Australia (longitude 60 to 180): Ascending preferred
        
        Args:
            aoi_wkt: Supported AOI WKT geometry used for centroid-based orbit heuristics.
                Uses self.aoi_wkt if None.
        
        Returns:
            str: Recommended orbit direction ('ASCENDING' or 'DESCENDING').
        """
        lon, _ = self._get_aoi_centroid(aoi_wkt)
        
        if self._EUROPE_AMERICA_LON_BOUNDS[0] <= lon < self._EUROPE_AMERICA_LON_BOUNDS[1]:
            return 'DESCENDING'
        else:
            return 'ASCENDING'
    
    def find_optimal_orbit(
        self,
        aoi_wkt: typing.Optional[str] = None,
        start_date: typing.Optional[str] = None,
        end_date: typing.Optional[str] = None,
        product_type: str = 'SLC',
        top: int = 100
    ) -> typing.Dict[str, typing.Any]:
        """Find the optimal orbit direction and relative orbit for maximum AOI coverage.
        
        This method searches both ascending and descending orbits and compares
        coverage to find the best configuration.
        
        Args:
            aoi_wkt: Area of Interest in WKT format. Uses self.aoi_wkt if None.
            start_date: Start date in ISO 8601 format. Uses self.start_date if None.
            end_date: End date in ISO 8601 format. Uses self.end_date if None.
            product_type: Product type to search ('SLC', 'GRD', etc.). Default 'SLC'.
            top: Maximum results fetched per direction during orbit analysis.
        
        Returns:
            Dict containing:
                - ascending: dict with orbits analysis for ascending
                - descending: dict with orbits analysis for descending
                - recommended: dict with optimal orbit_direction, relative_orbit, expected_coverage
        
        Example:
            >>> searcher = CopernicusDataSearcher()
            >>> result = searcher.find_optimal_orbit(
            ...     aoi_wkt='POLYGON((10 45, 12 45, 12 46, 10 46, 10 45))',
            ...     start_date='2024-08-01T00:00:00Z',
            ...     end_date='2024-08-31T00:00:00Z'
            ... )
            >>> print(f"Best: {result['recommended']['orbit_direction']} orbit {result['recommended']['relative_orbit']}")
        """
        aoi = aoi_wkt or self.aoi_wkt
        start = start_date or self.start_date
        end = end_date or self.end_date
        
        if aoi is None:
            raise ValueError("AOI WKT is required")
        if start is None or end is None:
            raise ValueError("Start and end dates are required")

        def normalize_relative_orbit(value):
            if value is None:
                return None
            if isinstance(value, float) and pd.isna(value):
                return None
            try:
                text = str(value).strip()
                if text == "":
                    return None
                text = text.lstrip("0") or "0"
                return int(text)
            except (TypeError, ValueError):
                return None
        
        results = {
            'ascending': {'orbits': {}, 'best_orbit': None, 'max_coverage': 0},
            'descending': {'orbits': {}, 'best_orbit': None, 'max_coverage': 0},
            'recommended': None
        }
        
        for direction in ['ASCENDING', 'DESCENDING']:
            logger.info(f"Analyzing {direction} orbits...")
            
            # Search without specific orbit to find all available
            self.query_by_filter(
                collection_name='SENTINEL-1',
                product_type=product_type,
                orbit_direction=direction,
                aoi_wkt=aoi,
                start_date=start,
                end_date=end,
                top=top,
                count=True
            )
            
            df = self.execute_query()
            
            if df.empty:
                continue
            
            # Extract relative orbit from attributes
            if 'Attributes' in df.columns:
                def get_relative_orbit(attrs):
                    if isinstance(attrs, list):
                        for attr in attrs:
                            if attr.get('Name') == 'relativeOrbitNumber':
                                return attr.get('Value')
                    return None
                
                df['relative_orbit'] = df['Attributes'].apply(get_relative_orbit)
            
            if 'relative_orbit' not in df.columns:
                df['relative_orbit'] = None
            df['relative_orbit'] = df['relative_orbit'].apply(normalize_relative_orbit)
            for col in ('RelativeOrbitNumber', 'relativeOrbitNumber'):
                if col in df.columns:
                    df['relative_orbit'] = df['relative_orbit'].fillna(
                        df[col].apply(normalize_relative_orbit)
                    )
            
            if 'relative_orbit' not in df.columns or df['relative_orbit'].isna().all():
                continue
            
            # Use coverage column already computed
            if 'coverage' not in df.columns or df['coverage'].isna().all():
                df['coverage'] = 50.0  # Default if shapely not available
            
            # Group by relative orbit
            orbit_stats = df.groupby('relative_orbit').agg({
                'coverage': ['mean', 'max', 'count']
            }).round(2)
            
            orbit_stats.columns = ['avg_coverage', 'max_coverage', 'count']
            orbit_stats = orbit_stats.reset_index()
            
            direction_key = direction.lower()
            for _, row in orbit_stats.iterrows():
                if pd.notna(row['relative_orbit']):
                    orbit = int(row['relative_orbit'])
                    results[direction_key]['orbits'][orbit] = {
                        'avg_coverage': float(row['avg_coverage']) if pd.notna(row['avg_coverage']) else 0,
                        'max_coverage': float(row['max_coverage']) if pd.notna(row['max_coverage']) else 0,
                        'count': int(row['count'])
                    }
            
            # Find best orbit for this direction
            if not orbit_stats.empty:
                # Filter out NaN values
                valid_stats = orbit_stats.dropna(subset=['avg_coverage', 'relative_orbit'])
                if not valid_stats.empty:
                    best_idx = valid_stats['avg_coverage'].idxmax()
                    best_orbit = int(valid_stats.loc[best_idx, 'relative_orbit'])
                    max_coverage = float(valid_stats.loc[best_idx, 'avg_coverage'])
                    
                    results[direction_key]['best_orbit'] = best_orbit
                    results[direction_key]['max_coverage'] = max_coverage
        
        # Determine overall recommendation
        asc_coverage = results['ascending']['max_coverage']
        desc_coverage = results['descending']['max_coverage']
        
        if asc_coverage > desc_coverage:
            results['recommended'] = {
                'orbit_direction': 'ASCENDING',
                'relative_orbit': results['ascending']['best_orbit'],
                'expected_coverage': asc_coverage
            }
        elif desc_coverage > asc_coverage:
            results['recommended'] = {
                'orbit_direction': 'DESCENDING',
                'relative_orbit': results['descending']['best_orbit'],
                'expected_coverage': desc_coverage
            }
        else:
            # Use regional preference if coverages are equal
            recommended_direction = self._get_recommended_orbit_direction(aoi)
            direction_key = recommended_direction.lower()
            results['recommended'] = {
                'orbit_direction': recommended_direction,
                'relative_orbit': results[direction_key]['best_orbit'],
                'expected_coverage': results[direction_key]['max_coverage']
            }
        
        return results
    
    def find_optimal_bursts(
        self,
        aoi_wkt: typing.Optional[str] = None,
        start_date: typing.Optional[str] = None,
        end_date: typing.Optional[str] = None,
        polarisation: str = 'VV',
        orbit_direction: typing.Optional[str] = None,
        relative_orbit_number: typing.Optional[int] = None,
        preferred_subswath: typing.Optional[typing.List[str]] = None
    ) -> pd.DataFrame:
        """Find optimal bursts covering the AOI with subswath preferences.
        
        Preferences:
        - IW1 preferred over IW2, IW3 preferred last (lower incident angle)
        - If orbit_direction not specified: Descending for EU/America, Ascending for Asia/Australia
        
        Args:
            aoi_wkt: Area of Interest in WKT format. Uses self.aoi_wkt if None.
            start_date: Start date in ISO 8601 format. Uses self.start_date if None.
            end_date: End date in ISO 8601 format. Uses self.end_date if None.
            polarisation: Polarisation channel ('VV', 'VH', 'HH', 'HV'). Default 'VV'.
            orbit_direction: Orbit direction ('ASCENDING' or 'DESCENDING'). Auto-detected if None.
            relative_orbit_number: Specific relative orbit to filter. None for all.
            preferred_subswath: List of subswaths in preference order. Default ['IW1', 'IW2', 'IW3'].
        
        Returns:
            pd.DataFrame: Optimized burst selection sorted by preference.
            
        Example:
            >>> searcher = CopernicusDataSearcher()
            >>> bursts = searcher.find_optimal_bursts(
            ...     aoi_wkt='POLYGON((10 45, 12 45, 12 46, 10 46, 10 45))',
            ...     start_date='2024-08-02T00:00:00Z',
            ...     end_date='2024-08-15T00:00:00Z',
            ...     polarisation='VV'
            ... )
        """
        aoi = aoi_wkt or self.aoi_wkt
        start = start_date or self.start_date
        end = end_date or self.end_date
        preferred = preferred_subswath or ['IW1', 'IW2', 'IW3']
        
        if aoi is None:
            raise ValueError("AOI WKT is required")
        if start is None or end is None:
            raise ValueError("Start and end dates are required")
        
        # Get recommended orbit direction if not specified
        direction = orbit_direction or self._get_recommended_orbit_direction(aoi)
        
        logger.info(f"Finding optimal bursts with {direction} orbit direction...")
        
        # Search bursts
        self.query_by_filter(
            burst_mode=True,
            orbit_direction=direction,
            aoi_wkt=aoi,
            start_date=start,
            end_date=end,
            polarisation_channels=polarisation,
            relative_orbit_number=relative_orbit_number,
            top=1000,
            count=True
        )
        
        df = self.execute_query()
        
        if df.empty:
            logger.warning("No bursts found for the specified parameters")
            return df
        
        # Add subswath priority based on preferences
        swath_priority = {swath: idx for idx, swath in enumerate(preferred)}
        default_priority = len(preferred)
        
        if 'SwathIdentifier' in df.columns:
            df['subswath_priority'] = df['SwathIdentifier'].apply(
                lambda x: swath_priority.get(x, default_priority)
            )
        else:
            df['subswath_priority'] = default_priority
        
        # Extract acquisition date
        if 'ContentDate' in df.columns:
            df['acquisition_date'] = pd.to_datetime(df['ContentDate'].apply(
                lambda x: x.get('Start') if isinstance(x, dict) else x
            )).dt.date
        
        # Sort by coverage (descending) then subswath priority (ascending)
        sort_columns = []
        sort_ascending = []
        
        if 'coverage' in df.columns:
            sort_columns.append('coverage')
            sort_ascending.append(False)
        
        sort_columns.append('subswath_priority')
        sort_ascending.append(True)
        
        df = df.sort_values(sort_columns, ascending=sort_ascending)
        
        # Log summary
        if 'SwathIdentifier' in df.columns:
            swath_counts = df['SwathIdentifier'].value_counts()
            logger.info(f"Found {len(df)} bursts:")
            for swath, count in swath_counts.items():
                logger.info(f"  {swath}: {count}")
        
        return df
    
    # -------------------------------------------------------------------------
    # Temporal Statistics Methods
    # -------------------------------------------------------------------------
    
    def compute_temporal_statistics(
        self,
        df: typing.Optional[pd.DataFrame] = None
    ) -> typing.Dict[str, typing.Any]:
        """Compute temporal statistics for search results.
        
        Args:
            df: DataFrame with search results. Uses self.df if None.
            
        Returns:
            Dict containing:
                - total_acquisitions: int
                - date_range: dict with start, end, span_days
                - temporal_gaps: dict with min_days, max_days, mean_days, median_days, std_days
                - acquisitions_by_month: dict
                - acquisitions_by_year: dict
                
        Example:
            >>> searcher = CopernicusDataSearcher()
            >>> searcher.query_by_filter(...)
            >>> searcher.execute_query()
            >>> stats = searcher.compute_temporal_statistics()
            >>> print(f"Mean revisit: {stats['temporal_gaps']['mean_days']:.1f} days")
        """
        data = df if df is not None else self.df
        
        if data is None or data.empty:
            logger.warning("No data available for temporal statistics")
            return {}
        
        # Extract acquisition dates
        dates = None
        if 'ContentDate' in data.columns:
            dates = pd.to_datetime(data['ContentDate'].apply(_extract_date_start), errors="coerce", utc=True)
        elif 'OriginDate' in data.columns:
            dates = pd.to_datetime(data['OriginDate'], errors="coerce", utc=True)
        
        if dates is None or dates.empty:
            logger.warning("No date column found in results")
            return {}
        
        dates = dates.dropna().sort_values()
        
        if len(dates) == 0:
            return {}
        
        # Calculate temporal gaps
        if len(dates) > 1:
            gaps = dates.diff().dropna()
            gaps_days = gaps.dt.total_seconds() / (24 * 3600)
            
            stats = {
                'total_acquisitions': len(dates),
                'date_range': {
                    'start': dates.min().isoformat(),
                    'end': dates.max().isoformat(),
                    'span_days': (dates.max() - dates.min()).days
                },
                'temporal_gaps': {
                    'min_days': float(gaps_days.min()),
                    'max_days': float(gaps_days.max()),
                    'mean_days': float(gaps_days.mean()),
                    'median_days': float(gaps_days.median()),
                    'std_days': float(gaps_days.std()) if len(gaps_days) > 1 else 0.0
                },
                'acquisitions_by_month': {str(k): int(v) for k, v in 
                                          dates.dt.strftime('%Y-%m').value_counts().sort_index().items()},
                'acquisitions_by_year': {int(k): int(v) for k, v in 
                                         dates.dt.year.value_counts().sort_index().items()}
            }
        else:
            stats = {
                'total_acquisitions': len(dates),
                'date_range': {
                    'start': dates.min().isoformat(),
                    'end': dates.max().isoformat(),
                    'span_days': 0
                },
                'temporal_gaps': None,
                'acquisitions_by_month': {},
                'acquisitions_by_year': {}
            }
        
        return stats
    
    def plot_temporal_distribution(
        self,
        df: typing.Optional[pd.DataFrame] = None,
        output_path: typing.Optional[str] = None,
        show: bool = True,
        figsize: typing.Tuple[int, int] = (14, 10)
    ) -> typing.Optional[str]:
        """Create and save a plot of temporal distribution of acquisitions.
        
        The plot includes:
        - Acquisition timeline scatter plot
        - Gap distribution histogram
        - Monthly acquisition counts
        - Cumulative acquisitions over time
        
        Args:
            df: DataFrame with search results. Uses self.df if None.
            output_path: Path to save the plot. Auto-generated if None.
            show: Whether to display the plot interactively.
            figsize: Figure size as (width, height) tuple.
            
        Returns:
            str: Path to the saved plot file, or None if not saved.
            
        Raises:
            ImportError: If matplotlib is not installed.
            
        Example:
            >>> searcher = CopernicusDataSearcher()
            >>> searcher.query_by_filter(...)
            >>> searcher.execute_query()
            >>> searcher.plot_temporal_distribution(output_path='./temporal_plot.png')
        """
        if not _MATPLOTLIB_AVAILABLE:
            raise ImportError("matplotlib is required for plotting. Install with: pip install matplotlib")
        
        data = df if df is not None else self.df
        
        if data is None or data.empty:
            logger.warning("No data available for plotting")
            return None
        
        # Extract acquisition dates
        dates = None
        if 'ContentDate' in data.columns:
            dates = pd.to_datetime(data['ContentDate'].apply(_extract_date_start), errors="coerce", utc=True)
        elif 'OriginDate' in data.columns:
            dates = pd.to_datetime(data['OriginDate'], errors="coerce", utc=True)
        
        if dates is None or dates.empty:
            logger.warning("No date column found in results")
            return None
        
        dates = dates.dropna().sort_values().reset_index(drop=True)
        
        if len(dates) < 2:
            logger.warning("Need at least 2 acquisitions for temporal plot")
            return None
        
        # Create figure with subplots
        fig, axes = plt.subplots(2, 2, figsize=figsize)
        fig.suptitle('Sentinel-1 Temporal Distribution Analysis', fontsize=14, fontweight='bold')
        
        # 1. Timeline scatter plot
        ax1 = axes[0, 0]
        ax1.scatter(dates, range(len(dates)), alpha=0.6, c='steelblue', s=50)
        ax1.set_xlabel('Acquisition Date')
        ax1.set_ylabel('Acquisition Index')
        ax1.set_title('Acquisition Timeline')
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax1.xaxis.set_major_locator(mdates.AutoDateLocator())
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')
        ax1.grid(True, alpha=0.3)
        
        # 2. Temporal gaps histogram
        ax2 = axes[0, 1]
        gaps = dates.diff().dropna()
        gaps_days = gaps.dt.total_seconds() / (24 * 3600)
        ax2.hist(gaps_days, bins=min(20, len(gaps_days)), color='coral', edgecolor='black', alpha=0.7)
        ax2.axvline(gaps_days.mean(), color='red', linestyle='--', 
                   label=f'Mean: {gaps_days.mean():.1f} days')
        ax2.axvline(gaps_days.median(), color='green', linestyle='--', 
                   label=f'Median: {gaps_days.median():.1f} days')
        ax2.legend()
        ax2.set_xlabel('Gap Duration (days)')
        ax2.set_ylabel('Frequency')
        ax2.set_title('Distribution of Temporal Gaps')
        ax2.grid(True, alpha=0.3)
        
        # 3. Monthly acquisition counts
        ax3 = axes[1, 0]
        monthly_counts = dates.dt.strftime('%Y-%m').value_counts().sort_index()
        months = list(monthly_counts.index)
        ax3.bar(months, monthly_counts.values, color='seagreen', alpha=0.7)
        ax3.set_xlabel('Month')
        ax3.set_ylabel('Number of Acquisitions')
        ax3.set_title('Acquisitions by Month')
        plt.setp(ax3.xaxis.get_majorticklabels(), rotation=45, ha='right')
        ax3.grid(True, alpha=0.3, axis='y')
        
        # 4. Cumulative acquisitions over time
        ax4 = axes[1, 1]
        cumulative = range(1, len(dates) + 1)
        ax4.plot(dates, cumulative, color='purple', linewidth=2)
        ax4.fill_between(dates, cumulative, alpha=0.3, color='purple')
        ax4.set_xlabel('Date')
        ax4.set_ylabel('Cumulative Acquisitions')
        ax4.set_title('Cumulative Acquisition Count')
        ax4.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax4.xaxis.set_major_locator(mdates.AutoDateLocator())
        plt.setp(ax4.xaxis.get_majorticklabels(), rotation=45, ha='right')
        ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # Save plot
        if output_path is None:
            output_path = f'temporal_distribution_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png'
        
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        logger.info(f"Plot saved to: {output_path}")
        
        if show:
            plt.show()
        else:
            plt.close()
        
        return output_path
    
    # -------------------------------------------------------------------------
    # Enhanced Download Methods
    # -------------------------------------------------------------------------
    
    def download_bursts(
        self,
        df: typing.Optional[pd.DataFrame] = None,
        output_dir: str = '.',
        username: typing.Optional[str] = None,
        password: typing.Optional[str] = None,
        retry_count: int = 3,
        verbose: bool = True,
        connect_timeout: float = REQUEST_TIMEOUT_SECONDS,
        read_timeout: typing.Optional[float] = None,
        state_file: typing.Optional[str] = None,
        resume_mode: str = 'off',
        backoff_base: float = 2.0,
        backoff_max: float = 60.0,
    ) -> typing.Dict[str, typing.Any]:
        """Download burst products from a DataFrame.
        
        This method handles CDSE authentication and downloads burst products
        via the on-demand processing API.
        
        Args:
            df: DataFrame with burst products to download. Uses self.df if None.
            output_dir: Directory to save downloaded bursts.
            username: CDSE username. Required for burst downloads.
            password: CDSE password. Required for burst downloads.
            retry_count: Number of retry attempts for failed downloads.
            verbose: Whether to print progress information.
            connect_timeout: HTTP connection timeout in seconds.
            read_timeout: HTTP read timeout in seconds (None => same as connect timeout).
            state_file: Optional JSON state file path for resumable runs.
            resume_mode: Resume mode ('off' or 'product').
            backoff_base: Base delay in seconds for retry backoff.
            backoff_max: Max delay in seconds for retry backoff.
            
        Returns:
            Dict containing:
                - downloaded: int count of successful downloads
                - failed: int count of failed downloads
                - details: list of dicts with download status per product
                
        Example:
            >>> searcher = CopernicusDataSearcher()
            >>> searcher.query_by_filter(burst_mode=True, ...)
            >>> df = searcher.execute_query()
            >>> result = searcher.download_bursts(
            ...     df=df,
            ...     output_dir='./bursts',
            ...     username='your_cdse_username',
            ...     password='your_cdse_password'
            ... )
        """
        data = df if df is not None else self.df
        
        if data is None or data.empty:
            logger.warning("No burst products to download")
            return {'downloaded': 0, 'failed': 0, 'skipped': 0, 'details': []}
        
        if username is None or password is None:
            raise ValueError("CDSE username and password are required for burst downloads. "
                           "Register at https://dataspace.copernicus.eu/")
        if resume_mode not in {'off', 'product'}:
            raise ValueError("resume_mode must be either 'off' or 'product'")
        
        # Ensure output directory exists
        output_path = Path(output_dir).absolute()
        output_path.mkdir(parents=True, exist_ok=True)

        state_store: typing.Optional[DownloadStateStore] = None
        if resume_mode != 'off':
            resolved_state_file = state_file or default_state_file(str(output_path))
            state_store = DownloadStateStore(resolved_state_file)
        
        # Create token manager for automatic token refresh
        if verbose:
            print("🔐 Authenticating with CDSE...")
        
        try:
            token_manager = TokenManager(username, password)
            # Trigger initial authentication
            token_manager.get_access_token()
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            raise
        
        summary = {
            'downloaded': 0,
            'failed': 0,
            'skipped': 0,
            'details': []
        }
        
        total = len(data)
        for idx, row in data.iterrows():
            burst_id = row.get('Id')
            burst_num = row.get('BurstId', 'unknown')
            
            if not burst_id:
                summary['failed'] += 1
                summary['details'].append({
                    'burst_id': None,
                    'status': 'error',
                    'error': 'No burst ID found'
                })
                continue
            
            if verbose:
                print(f"📥 Downloading burst {idx + 1}/{total} (BurstId: {burst_num})...")

            if state_store is not None:
                existing = state_store.get(str(burst_id))
                existing_output = existing.get('output_path') if isinstance(existing, dict) else None
                if existing and existing.get('status') == 'success' and existing_output and is_non_empty_file(existing_output):
                    summary['skipped'] += 1
                    summary['details'].append({
                        'burst_id': burst_id,
                        'burst_num': burst_num,
                        'status': 'skipped',
                        'reason': 'already_downloaded'
                    })
                    if verbose:
                        print("   ⏭️  Skipped (already downloaded)")
                    continue
            
            success = False
            last_error = None
            
            for attempt in range(retry_count):
                try:
                    download_burst_on_demand(
                        burst_id=burst_id,
                        token=token_manager,
                        output_dir=output_path,
                        connect_timeout=connect_timeout,
                        read_timeout=read_timeout,
                        retry_count=1,
                        state_file=state_file,
                        resume_mode=resume_mode,
                        backoff_base=backoff_base,
                        backoff_max=backoff_max,
                    )
                    success = True
                    break
                except Exception as e:
                    last_error = str(e)
                    if verbose and attempt < retry_count - 1:
                        print(f"   ⚠️  Attempt {attempt + 1} failed, retrying...")
                    if attempt < retry_count - 1:
                        delay = _compute_backoff_delay(attempt, backoff_base=backoff_base, backoff_max=backoff_max)
                        time.sleep(delay)
            
            if success:
                summary['downloaded'] += 1
                summary['details'].append({
                    'burst_id': burst_id,
                    'burst_num': burst_num,
                    'status': 'success'
                })
                if verbose:
                    print(f"   ✅ Downloaded successfully")
            else:
                summary['failed'] += 1
                summary['details'].append({
                    'burst_id': burst_id,
                    'burst_num': burst_num,
                    'status': 'failed',
                    'error': last_error
                })
                if verbose:
                    print(f"   ❌ Failed: {last_error}")
        
        if verbose:
            print(
                f"\n📊 Download complete: {summary['downloaded']} succeeded, "
                f"{summary['failed']} failed, {summary['skipped']} skipped"
            )
        
        return summary
    
    def download_products(
        self,
        df: typing.Optional[pd.DataFrame] = None,
        output_dir: str = '.',
        config_file: str = '.s5cfg',
        mode: str = 'fast',
        retry_count: int = 3,
        validate: bool = True,
        verbose: bool = True,
        show_progress: bool = True,
        state_file: typing.Optional[str] = None,
        resume_mode: typing.Optional[str] = None,
        s5cmd_retry_count: typing.Optional[int] = None,
        max_workers: typing.Optional[int] = None,
        backoff_base: float = 2.0,
        backoff_max: float = 60.0,
    ) -> typing.Dict[str, typing.Any]:
        """Download multiple SLC/GRD products from a DataFrame.
        
        This method downloads products via S3 using s5cmd with retry logic
        and optional validation.
        
        Args:
            df: DataFrame with products to download. Uses self.df if None.
            output_dir: Directory to save downloaded products.
            config_file: Path to s5cmd configuration file.
            mode: Download mode ('fast' for s5cmd, 'safe' for resumable native downloads).
            retry_count: Number of retry attempts for failed downloads.
            validate: Whether to validate downloaded files (check manifest.safe exists).
            verbose: Whether to print progress information.
            show_progress: Whether to show tqdm progress bar.
            state_file: Optional JSON state file path for resumable runs.
            resume_mode: Deprecated legacy resume selector. Prefer ``mode``.
            s5cmd_retry_count: Optional internal retry count for s5cmd.
            max_workers: Optional worker count for s5cmd.
            backoff_base: Base delay in seconds for retry backoff.
            backoff_max: Max delay in seconds for retry backoff.
            
        Returns:
            Dict containing:
                - downloaded: int count of successful downloads
                - failed: int count of failed downloads
                - details: list of dicts with download status per product
                
        Example:
            >>> searcher = CopernicusDataSearcher()
            >>> searcher.query_by_filter(collection_name='SENTINEL-1', product_type='SLC', ...)
            >>> df = searcher.execute_query()
            >>> result = searcher.download_products(df=df, output_dir='./data')
        """
        data = df if df is not None else self.df
        
        if data is None or data.empty:
            logger.warning("No products to download")
            return {'downloaded': 0, 'failed': 0, 'skipped': 0, 'details': []}
        effective_mode = _resolve_product_download_mode(mode, resume_mode=resume_mode)
        
        # Ensure output directory exists
        abs_output_dir = os.path.abspath(output_dir)
        os.makedirs(abs_output_dir, exist_ok=True)

        use_native = effective_mode == 'safe'
        state_store: typing.Optional[DownloadStateStore] = None
        if not use_native and resume_mode not in (None, 'off'):
            resolved_state_file = state_file or default_state_file(abs_output_dir)
            state_store = DownloadStateStore(resolved_state_file)
        
        summary = {
            'downloaded': 0,
            'failed': 0,
            'skipped': 0,
            'details': []
        }
        
        total = len(data)
        for idx, row in data.iterrows():
            product_name = row.get('Name', f'product_{idx}')
            s3_path = row.get('S3Path')
            content_length = row.get('ContentLength', 0)
            
            if not s3_path:
                summary['failed'] += 1
                summary['details'].append({
                    'name': product_name,
                    'status': 'error',
                    'error': 'No S3Path found'
                })
                continue
            
            if verbose:
                print(f"📥 Downloading {idx + 1}/{total}: {product_name}...")

            product_dir = os.path.join(abs_output_dir, product_name)
            manifest_path = os.path.join(product_dir, 'manifest.safe')

            if not use_native and is_product_complete(product_dir):
                if state_store is not None:
                    state_store.mark(
                        product_name,
                        'success',
                        output_path=product_dir,
                        extra={'s3_path': s3_path},
                    )
                summary['skipped'] += 1
                summary['details'].append({
                    'name': product_name,
                    'status': 'skipped',
                    'reason': 'already_downloaded'
                })
                if verbose:
                    print("   ⏭️  Skipped (already downloaded)")
                continue

            if state_store is not None:
                existing = state_store.get(product_name)
                existing_output = existing.get('output_path') if isinstance(existing, dict) else None
                if existing and existing.get('status') == 'success' and existing_output and is_product_complete(existing_output):
                    summary['skipped'] += 1
                    summary['details'].append({
                        'name': product_name,
                        'status': 'skipped',
                        'reason': 'already_downloaded'
                    })
                    if verbose:
                        print("   ⏭️  Skipped (already downloaded)")
                    continue
            
            success = False
            last_error = None
            
            for attempt in range(retry_count):
                try:
                    if use_native:
                        result = download_s3_resumable(
                            s3_path=s3_path,
                            output_dir=abs_output_dir,
                            config_file=config_file,
                            download_all=True,
                            state_file=state_file,
                            state_item_id=product_name,
                            show_progress=show_progress,
                            attempts=attempt + 1,
                            persist_state=True,
                        )
                        if result.status == 'skipped':
                            summary['skipped'] += 1
                            summary['details'].append({
                                'name': product_name,
                                'status': 'skipped',
                                'reason': 'already_downloaded'
                            })
                            if verbose:
                                print("   ⏭️  Skipped (already downloaded)")
                            success = None
                            break
                        if validate and not is_product_complete(result.output_path):
                            raise ValueError("manifest.safe not found - download may be incomplete")
                    else:
                        if state_store is not None:
                            state_store.mark(
                                product_name,
                                'in_progress',
                                attempts=attempt + 1,
                                output_path=product_dir,
                                extra={'s3_path': s3_path},
                            )
                        pull_down(
                            s3_path=s3_path,
                            output_dir=abs_output_dir,
                            config_file=config_file,
                            total_size=content_length,
                            show_progress=show_progress,
                            retry_count=1,
                            s5cmd_retry_count=s5cmd_retry_count,
                            max_workers=max_workers,
                            backoff_base=backoff_base,
                            backoff_max=backoff_max,
                        )
                        
                        # Validate if enabled
                        if validate:
                            if os.path.isdir(product_dir) and not os.path.exists(manifest_path):
                                raise ValueError("manifest.safe not found - download may be incomplete")
                    
                    success = True
                    if state_store is not None:
                        state_store.mark(
                            product_name,
                            'success',
                            attempts=attempt + 1,
                            output_path=product_dir,
                            extra={'s3_path': s3_path},
                        )
                    break
                    
                except Exception as e:
                    last_error = str(e)
                    if state_store is not None:
                        state_store.mark(
                            product_name,
                            'failed',
                            attempts=attempt + 1,
                            error=last_error,
                            output_path=product_dir,
                            extra={'s3_path': s3_path},
                        )
                    if verbose and attempt < retry_count - 1:
                        print(f"   ⚠️  Attempt {attempt + 1} failed, retrying...")
                    if attempt < retry_count - 1:
                        delay = _compute_backoff_delay(attempt, backoff_base=backoff_base, backoff_max=backoff_max)
                        time.sleep(delay)
            
            if success is None:
                continue
            if success:
                summary['downloaded'] += 1
                summary['details'].append({
                    'name': product_name,
                    'status': 'success'
                })
                if verbose:
                    print(f"   ✅ Downloaded successfully")
            else:
                summary['failed'] += 1
                summary['details'].append({
                    'name': product_name,
                    'status': 'failed',
                    'error': last_error
                })
                if verbose:
                    print(f"   ❌ Failed: {last_error}")
        
        if verbose:
            print(
                f"\n📊 Download complete: {summary['downloaded']} succeeded, "
                f"{summary['failed']} failed, {summary['skipped']} skipped"
            )
        
        return summary
