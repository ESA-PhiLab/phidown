"""Assemble downloaded Sentinel-1 SLC bursts into an ESA SAFE product.

The CDSE burst catalogue exposes burst measurements as small, independently
usable downloads.  A burst on its own is not a normal Sentinel-1 SAFE: its
measurement rows and the line/time-dependent annotation records must be
assembled with neighbouring bursts.  This module performs that local
assembly without depending on the online ASF ``burst2safe`` service.

Supported input layout
----------------------
The primary input is one or more burst SAFE directories, such as those made
by the CDSE Sentinel-1 burst extractor::

    collection/
      S1..._001.SAFE/measurement/*.tiff
      S1..._001.SAFE/annotation/*.xml
      S1..._002.SAFE/measurement/*.tiff
      S1..._002.SAFE/annotation/*.xml

A directory containing those SAFE directories may be passed instead.  Each
input SAFE must contain exactly one burst for each measurement file.  The
measurement is expected to be an uncompressed Sentinel-1 complex-int16 TIFF
(or another TIFF representation that can be losslessly converted to that
layout).

This is intentionally a local, deterministic operation: it never downloads
or modifies source files.  The generated SAFE is written atomically into the
requested output directory.
"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import struct
import tempfile
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence
from xml.sax.saxutils import escape


class BurstMergeError(ValueError):
    """Raised when burst inputs cannot form a valid assembled SAFE."""


@dataclass
class _BurstRecord:
    """Normalized metadata for one downloaded burst."""

    safe_path: Path
    data_path: Path
    product_path: Path
    product: ET.Element
    calibration: ET.Element | None
    noise: ET.Element | None
    rfi: ET.Element | None
    manifest: ET.Element | None
    swath: str
    polarization: str
    burst_id: int
    absolute_orbit: int
    relative_orbit: int | None
    platform: str
    mode: str
    datatake_id: str
    start: datetime
    stop: datetime
    lines: int
    samples: int


@dataclass
class _OutputFile:
    """A file emitted into the SAFE and its manifest representation."""

    path: Path
    kind: str
    rep_id: str
    unit_type: str
    data_id: str
    metadata_id: str


_TIFF_SUFFIXES = {".tif", ".tiff"}
_PRODUCT_PREFIXES = ("calibration-", "noise-", "rfi-")
_PLATFORM_RE = re.compile(r"^(S1[ABC])(?:_|$)", re.IGNORECASE)
_SWATH_POL_RE = re.compile(r"s1[abc]-(?P<swath>iw[1-3]|ew[1-5])-slc-(?P<pol>vv|vh|hh|hv)", re.IGNORECASE)
_DATE_TOKEN_RE = re.compile(r"^\d{8}T\d{6}$")


def _local_name(tag: str) -> str:
    """Return an XML tag without its namespace URI."""

    return tag.rsplit("}", 1)[-1]


def _child(element: ET.Element | None, name: str) -> ET.Element | None:
    if element is None:
        return None
    for candidate in list(element):
        if _local_name(candidate.tag) == name:
            return candidate
    return None


def _children(element: ET.Element | None, name: str) -> list[ET.Element]:
    if element is None:
        return []
    return [candidate for candidate in list(element) if _local_name(candidate.tag) == name]


def _descendants(element: ET.Element | None, name: str) -> list[ET.Element]:
    if element is None:
        return []
    return [candidate for candidate in element.iter() if _local_name(candidate.tag) == name]


def _first_descendant(element: ET.Element | None, name: str) -> ET.Element | None:
    matches = _descendants(element, name)
    return matches[0] if matches else None


def _text(element: ET.Element | None, *path: str) -> str | None:
    current = element
    for part in path:
        current = _child(current, part)
        if current is None:
            return None
    return current.text.strip() if current.text else None


def _first_text(element: ET.Element | None, *names: str) -> str | None:
    for name in names:
        candidate = _first_descendant(element, name)
        if candidate is not None and candidate.text:
            return candidate.text.strip()
    return None


def _set_text(element: ET.Element | None, value: object) -> None:
    if element is not None:
        element.text = str(value)


def _set_path_text(element: ET.Element, value: object, *path: str) -> None:
    current: ET.Element | None = element
    for part in path:
        current = _child(current, part)
        if current is None:
            return
    _set_text(current, value)


def _parse_time(value: str | None) -> datetime:
    if not value:
        raise BurstMergeError("Burst metadata does not contain a UTC time")
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise BurstMergeError(f"Invalid Sentinel-1 UTC time: {value!r}") from exc
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def _format_time(value: datetime) -> str:
    """Use the ISO representation used by Sentinel-1 annotation XML."""

    return value.isoformat(timespec="microseconds")


def _parse_int(value: str | None, field: str) -> int:
    if value is None or not value.strip():
        raise BurstMergeError(f"Missing {field} in burst metadata")
    try:
        return int(value)
    except ValueError as exc:
        raise BurstMergeError(f"Invalid {field}: {value!r}") from exc


def _parse_safe_name(path: Path) -> dict[str, str | int | None]:
    """Extract fallback identifiers from a Sentinel-1 SAFE directory name."""

    stem = path.name[:-5] if path.name.upper().endswith(".SAFE") else path.name
    parts = stem.split("_")
    result: dict[str, str | int | None] = {
        "platform": None,
        "mode": None,
        "orbit": None,
        "datatake": None,
    }
    if parts:
        result["platform"] = parts[0].upper()
    if len(parts) > 1:
        result["mode"] = parts[1].upper()
    date_indexes = [index for index, part in enumerate(parts) if _DATE_TOKEN_RE.match(part)]
    if date_indexes:
        date_index = date_indexes[0]
        if len(parts) > date_index + 2:
            try:
                result["orbit"] = int(parts[date_index + 2])
            except ValueError:
                pass
        if len(parts) > date_index + 3:
            result["datatake"] = parts[date_index + 3].upper()
    return result


def _read_xml(path: Path) -> ET.Element:
    try:
        return ET.parse(path).getroot()
    except (ET.ParseError, OSError) as exc:
        raise BurstMergeError(f"Could not read XML metadata {path}: {exc}") from exc


def _component_from_xml(root: ET.Element, kind: str, swath: str | None = None, polarization: str | None = None) -> ET.Element | None:
    """Find a product/calibration component in standalone or combined XML."""

    root_kind = _local_name(root.tag)
    if root_kind == kind:
        # A normal standalone annotation has the component as its root.
        if kind != "product" or _child(root, "swathTiming") is not None:
            return root

    # CDSE/ASF combined metadata stores <product>/<noise>/... wrappers with
    # swath, polarisation, and a <content> child.
    for candidate in root.iter():
        if _local_name(candidate.tag) != kind:
            continue
        candidate_swath = _first_text(_child(candidate, "swath"), "swath") or _text(candidate, "swath")
        candidate_pol = _first_text(_child(candidate, "polarisation"), "polarisation") or _text(candidate, "polarisation")
        if swath and candidate_swath and candidate_swath.upper() != swath.upper():
            continue
        if polarization and candidate_pol and candidate_pol.upper() != polarization.upper():
            continue
        content = _child(candidate, "content")
        if kind == "noise" and content is None and _child(candidate, "adsHeader") is None:
            # Combined metadata also contains individual noise-vector elements
            # inside product/generalAnnotation. They are not a standalone XML
            # component; the swath/polarisation wrapper is the component.
            continue
        if content is not None:
            return content
        return candidate
    return None


def _manifest_root(root: ET.Element | None) -> ET.Element | None:
    if root is None:
        return None
    if _local_name(root.tag) == "XFDU":
        return root
    for candidate in root.iter():
        if _local_name(candidate.tag) == "XFDU":
            return candidate
    return None


def _manifest_field(manifest: ET.Element | None, object_id: str, name: str) -> str | None:
    if manifest is None:
        return None
    for candidate in _descendants(manifest, "metadataObject"):
        if candidate.get("ID") == object_id:
            value = _first_descendant(candidate, name)
            if value is not None and value.text:
                return value.text.strip()
    return None


def _manifest_component(path: Path, kind: str, swath: str, polarization: str) -> ET.Element | None:
    """Read one component from an input SAFE's annotation files."""

    annotation_dir = path / "annotation"
    if not annotation_dir.is_dir():
        return None
    candidates: list[Path] = []
    if kind == "product":
        candidates = sorted(
            file
            for file in annotation_dir.glob("*.xml")
            if not file.name.lower().startswith(_PRODUCT_PREFIXES)
        )
    elif kind in {"calibration", "noise"}:
        candidates = sorted((annotation_dir / "calibration").glob(f"{kind}-*.xml"))
    elif kind == "rfi":
        candidates = sorted((annotation_dir / "rfi").glob("rfi-*.xml"))
    for candidate_path in candidates:
        component = _component_from_xml(_read_xml(candidate_path), kind, swath, polarization)
        if component is not None:
            return component
    return None


def _measurement_hint(path: Path) -> tuple[str | None, str | None]:
    match = _SWATH_POL_RE.search(path.name)
    if not match:
        return None, None
    return match.group("swath").upper(), match.group("pol").upper()


def _annotation_candidates(safe_path: Path) -> list[Path]:
    annotation_dir = safe_path / "annotation"
    if not annotation_dir.is_dir():
        return []
    return sorted(
        file
        for file in annotation_dir.glob("*.xml")
        if not file.name.lower().startswith(_PRODUCT_PREFIXES)
    )


def _product_for_measurement(safe_path: Path, data_path: Path) -> tuple[Path, ET.Element, str, str]:
    hint_swath, hint_pol = _measurement_hint(data_path)
    for candidate_path in _annotation_candidates(safe_path):
        root = _read_xml(candidate_path)
        component = _component_from_xml(root, "product", hint_swath, hint_pol)
        if component is None:
            continue
        swath = (_first_text(component, "swath") or hint_swath or "").upper()
        polarization = (_first_text(component, "polarisation") or hint_pol or "").upper()
        if swath and polarization:
            return candidate_path, component, swath, polarization
    raise BurstMergeError(
        f"Could not find product annotation for {data_path}. "
        "Expected an XML file in the SAFE's annotation directory."
    )


def _read_manifest_for_safe(safe_path: Path) -> ET.Element | None:
    path = safe_path / "manifest.safe"
    return _manifest_root(_read_xml(path)) if path.is_file() else None


def _record_from_paths(safe_path: Path, data_path: Path) -> _BurstRecord:
    product_path, product, swath, polarization = _product_for_measurement(safe_path, data_path)
    burst_list = _child(_child(product, "swathTiming"), "burstList")
    bursts = _children(burst_list, "burst")
    if len(bursts) != 1:
        raise BurstMergeError(
            f"{product_path} contains {len(bursts)} bursts; each input SAFE must contain exactly one burst"
        )
    burst = bursts[0]
    burst_id = _parse_int(_first_text(burst, "burstId"), "burstId")

    lines = _parse_int(_text(product, "swathTiming", "linesPerBurst"), "linesPerBurst")
    samples = _parse_int(_text(product, "swathTiming", "samplesPerBurst"), "samplesPerBurst")
    start_value = _first_text(burst, "azimuthTime", "sensingTime") or _first_text(
        product, "productFirstLineUtcTime", "startTime"
    )
    start = _parse_time(start_value)
    stop_value = _first_text(product, "productLastLineUtcTime") or _first_text(product, "stopTime")
    if stop_value:
        stop = _parse_time(stop_value)
    else:
        interval_text = _first_text(product, "azimuthTimeInterval")
        interval = float(interval_text) if interval_text else 0.0
        stop = start + timedelta(seconds=max(0, lines - 1) * interval)

    fallback = _parse_safe_name(safe_path)
    manifest = _read_manifest_for_safe(safe_path)
    absolute_orbit_text = _first_text(product, "absoluteOrbitNumber") or _manifest_field(
        manifest, "measurementOrbitReference", "orbitNumber"
    )
    absolute_orbit = (
        _parse_int(absolute_orbit_text, "absoluteOrbitNumber")
        if absolute_orbit_text
        else _parse_int(str(fallback["orbit"]), "absolute orbit")
        if fallback["orbit"] is not None
        else 0
    )
    relative_text = _manifest_field(manifest, "measurementOrbitReference", "relativeOrbitNumber")
    relative_orbit = _parse_int(relative_text, "relative orbit") if relative_text else None
    platform = (_first_text(product, "missionId") or str(fallback["platform"] or "")).upper()
    mode = (_first_text(product, "mode") or str(fallback["mode"] or "IW")).upper()
    datatake_text = _first_text(product, "missionDataTakeId") or str(fallback["datatake"] or "")
    if datatake_text.isdigit():
        datatake_id = f"{int(datatake_text):06d}"
    else:
        datatake_id = datatake_text.upper()

    return _BurstRecord(
        safe_path=safe_path,
        data_path=data_path,
        product_path=product_path,
        product=product,
        calibration=_manifest_component(safe_path, "calibration", swath, polarization),
        noise=_manifest_component(safe_path, "noise", swath, polarization),
        rfi=_manifest_component(safe_path, "rfi", swath, polarization),
        manifest=manifest,
        swath=swath,
        polarization=polarization,
        burst_id=burst_id,
        absolute_orbit=absolute_orbit,
        relative_orbit=relative_orbit,
        platform=platform,
        mode=mode,
        datatake_id=datatake_id,
        start=start,
        stop=stop,
        lines=lines,
        samples=samples,
    )


def _as_named_component(root: ET.Element | None, kind: str) -> ET.Element | None:
    """Turn a combined-metadata ``content`` element into a component root."""
    if root is None:
        return None
    if _local_name(root.tag) == kind:
        return ET.fromstring(ET.tostring(root, encoding="utf-8"))
    component = ET.Element(kind)
    component.extend(ET.fromstring(ET.tostring(child, encoding="utf-8")) for child in list(root))
    return component


def _localize_raw_product(product: ET.Element, burst_index: int, lines: int) -> tuple[ET.Element, ET.Element]:
    """Select one burst from a full combined annotation and rebase its rows."""
    local_product = _as_product(product)
    timing = _child(local_product, "swathTiming")
    source_bursts = _children(_child(timing, "burstList"), "burst")
    if burst_index < 0 or burst_index >= len(source_bursts):
        raise BurstMergeError(f"Burst index {burst_index} is outside the annotation burst list")
    selected = ET.fromstring(ET.tostring(source_bursts[burst_index], encoding="utf-8"))
    selected_list = ET.Element("burstList", {"count": "1"})
    selected_list.append(selected)
    _replace_child(timing, _child(timing, "burstList"), selected_list)

    start_line = burst_index * lines
    geo = _child(local_product, "geolocationGrid")
    source_grid = _child(geo, "geolocationGridPointList")
    if source_grid is not None:
        local_grid = ET.Element("geolocationGridPointList")
        for point in _children(source_grid, "geolocationGridPoint"):
            copy = ET.fromstring(ET.tostring(point, encoding="utf-8"))
            line = _first_descendant(copy, "line")
            if line is None or not line.text:
                continue
            try:
                value = float(line.text)
            except ValueError:
                continue
            if start_line <= value < start_line + lines:
                rebased = value - start_line
                _set_text(line, int(rebased) if rebased.is_integer() else rebased)
                local_grid.append(copy)
        local_grid.set("count", str(len(local_grid)))
        _replace_child(geo, source_grid, local_grid)

    burst_start = _first_text(selected, "azimuthTime", "sensingTime")
    if burst_start:
        _set_path_text(local_product, burst_start, "adsHeader", "startTime")
        _set_path_text(local_product, burst_start, "imageAnnotation", "imageInformation", "productFirstLineUtcTime")
    interval_text = _first_text(local_product, "azimuthTimeInterval")
    if burst_start and interval_text:
        try:
            local_stop = _parse_time(burst_start) + timedelta(seconds=max(0, lines - 1) * float(interval_text))
            _set_path_text(local_product, _format_time(local_stop), "adsHeader", "stopTime")
            _set_path_text(local_product, _format_time(local_stop), "imageAnnotation", "imageInformation", "productLastLineUtcTime")
        except ValueError:
            pass
    image_info = _child(_child(local_product, "imageAnnotation"), "imageInformation")
    if image_info is not None:
        image_info.attrib.pop("numberOfLines", None)
    _set_path_text(local_product, lines, "imageAnnotation", "imageInformation", "numberOfLines")
    return local_product, selected


def _format_line_value(value: float) -> str:
    return str(int(value)) if value.is_integer() else f"{value:g}"


def _transform_noise_azimuth_vector(
    vector: ET.Element,
    offset: int = 0,
    line_start: int | None = None,
    line_stop: int | None = None,
) -> bool:
    """Offset/filter a noise azimuth vector and its matching LUT."""
    line = _first_descendant(vector, "line")
    if line is None or not line.text:
        return True
    raw_values = line.text.split()
    values: list[float] = []
    for value in raw_values:
        try:
            values.append(float(value))
        except ValueError:
            return True
    keep_indices = [
        index
        for index, value in enumerate(values)
        if line_start is None or (line_start <= value < (line_stop if line_stop is not None else float("inf")))
    ]
    if not keep_indices:
        return False
    transformed = [values[index] - (line_start or 0) + offset for index in keep_indices]
    line.text = " ".join(_format_line_value(value) for value in transformed)
    line.set("count", str(len(transformed)))
    first = _first_descendant(vector, "firstAzimuthLine")
    last = _first_descendant(vector, "lastAzimuthLine")
    if first is not None:
        _set_text(first, _format_line_value(transformed[0]))
    if last is not None:
        _set_text(last, _format_line_value(transformed[-1]))
    lut = _first_descendant(vector, "noiseAzimuthLut")
    if lut is not None and lut.text:
        lut_values = lut.text.split()
        lut.text = " ".join(lut_values[index] for index in keep_indices if index < len(lut_values))
        lut.set("count", str(len(lut.text.split())))
    return True


def _localize_raw_auxiliary(root: ET.Element | None, kind: str, burst_index: int, lines: int) -> ET.Element | None:
    component = _as_named_component(root, kind)
    if component is None:
        return None
    start_line = burst_index * lines
    stop_line = start_line + lines
    for vector_list in [item for item in component.iter() if _local_name(item.tag).endswith("VectorList")]:
        if kind == "noise" and _local_name(vector_list.tag) == "noiseAzimuthVectorList":
            for index, vector in enumerate(list(vector_list)):
                copy = ET.fromstring(ET.tostring(vector, encoding="utf-8"))
                if not _transform_noise_azimuth_vector(copy, line_start=start_line, line_stop=stop_line):
                    vector_list.remove(vector)
                else:
                    vector_list.remove(vector)
                    vector_list.insert(index, copy)
            vector_list.set("count", str(len(vector_list)))
            continue
        for vector in list(vector_list):
            line = _first_descendant(vector, "line")
            if line is None or not line.text:
                continue
            try:
                value = float(line.text) - start_line
            except ValueError:
                continue
            if value < 0 or value >= lines:
                vector_list.remove(vector)
            else:
                _set_text(line, int(value) if value.is_integer() else value)
        vector_list.set("count", str(len(vector_list)))
    return component


def _record_from_raw_tree(
    data_path: Path,
    metadata_path: Path,
    slc_name: str,
    swath: str,
    polarization: str,
    burst_index: int,
) -> _BurstRecord:
    root = _read_xml(metadata_path)
    source_product = _component_from_xml(root, "product", swath, polarization)
    if source_product is None:
        raise BurstMergeError(f"No {swath}/{polarization} product annotation found in {metadata_path}")
    full_product = _as_product(source_product)
    lines = _parse_int(_text(full_product, "swathTiming", "linesPerBurst"), "linesPerBurst")
    samples = _parse_int(_text(full_product, "swathTiming", "samplesPerBurst"), "samplesPerBurst")
    product, selected_burst = _localize_raw_product(full_product, burst_index, lines)
    burst_id = _parse_int(_first_text(selected_burst, "burstId"), "burstId")
    start = _parse_time(_first_text(selected_burst, "azimuthTime", "sensingTime"))
    stop_text = _first_text(product, "productLastLineUtcTime")
    stop = _parse_time(stop_text) if stop_text else start + timedelta(seconds=max(0, lines - 1) * float(_first_text(product, "azimuthTimeInterval") or 0))
    manifest = _manifest_root(root)
    fallback = _parse_safe_name(Path(slc_name + ".SAFE"))
    absolute_text = _first_text(product, "absoluteOrbitNumber") or _manifest_field(manifest, "measurementOrbitReference", "orbitNumber")
    absolute_orbit = _parse_int(absolute_text, "absoluteOrbitNumber") if absolute_text else _parse_int(str(fallback["orbit"]), "absolute orbit")
    relative_text = _manifest_field(manifest, "measurementOrbitReference", "relativeOrbitNumber")
    relative_orbit = _parse_int(relative_text, "relative orbit") if relative_text else None
    platform = (_first_text(product, "missionId") or str(fallback["platform"] or "")).upper()
    mode = (_first_text(product, "mode") or str(fallback["mode"] or "IW")).upper()
    datatake_text = _first_text(product, "missionDataTakeId") or str(fallback["datatake"] or "")
    datatake_id = f"{int(datatake_text):06d}" if datatake_text.isdigit() else datatake_text.upper()
    return _BurstRecord(
        safe_path=metadata_path.parent,
        data_path=data_path,
        product_path=metadata_path,
        product=product,
        calibration=_localize_raw_auxiliary(_component_from_xml(root, "calibration", swath, polarization), "calibration", burst_index, lines),
        noise=_localize_raw_auxiliary(_component_from_xml(root, "noise", swath, polarization), "noise", burst_index, lines),
        rfi=_localize_raw_auxiliary(_component_from_xml(root, "rfi", swath, polarization), "rfi", burst_index, lines),
        manifest=manifest,
        swath=swath.upper(),
        polarization=polarization.upper(),
        burst_id=burst_id,
        absolute_orbit=absolute_orbit,
        relative_orbit=relative_orbit,
        platform=platform,
        mode=mode,
        datatake_id=datatake_id,
        start=start,
        stop=stop,
        lines=lines,
        samples=samples,
    )


def _records_from_tree(path: Path) -> list[_BurstRecord]:
    """Load the JSON tree format used by downloaded burst extractors."""
    import json

    try:
        tree = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BurstMergeError(f"Could not read burst tree {path}: {exc}") from exc
    if not isinstance(tree, dict):
        raise BurstMergeError("Burst tree JSON must be an object keyed by SLC product name")
    records: list[_BurstRecord] = []
    for slc_name, swaths in tree.items():
        if not isinstance(swaths, dict):
            raise BurstMergeError(f"Invalid swath mapping for {slc_name!r}")
        for swath, polarizations in swaths.items():
            if not isinstance(polarizations, dict):
                raise BurstMergeError(f"Invalid polarization mapping for {slc_name}/{swath}")
            for polarization, burst_map in polarizations.items():
                if not isinstance(burst_map, dict):
                    raise BurstMergeError(f"Invalid burst mapping for {slc_name}/{swath}/{polarization}")
                for raw_index, spec in burst_map.items():
                    if not isinstance(spec, dict) or "DATA" not in spec or "METADATA" not in spec:
                        raise BurstMergeError(f"Burst {slc_name}/{swath}/{polarization}/{raw_index} needs DATA and METADATA")
                    data_path = Path(spec["DATA"]).expanduser()
                    metadata_path = Path(spec["METADATA"]).expanduser()
                    if not data_path.is_absolute():
                        data_path = path.parent / data_path
                    if not metadata_path.is_absolute():
                        metadata_path = path.parent / metadata_path
                    try:
                        burst_index = int(raw_index)
                    except (TypeError, ValueError) as exc:
                        raise BurstMergeError(f"Invalid burst index {raw_index!r}") from exc
                    records.append(_record_from_raw_tree(data_path.resolve(), metadata_path.resolve(), str(slc_name), str(swath), str(polarization), burst_index))
    if not records:
        raise BurstMergeError(f"Burst tree contains no burst records: {path}")
    return records


def _is_burst_safe(path: Path) -> bool:
    if not path.is_dir():
        return False
    measurement = path / "measurement"
    annotation = path / "annotation"
    return measurement.is_dir() and annotation.is_dir() and any(
        item.is_file() and item.suffix.lower() in _TIFF_SUFFIXES for item in measurement.iterdir()
    )


def discover_burst_safes(inputs: Iterable[str | os.PathLike[str]]) -> list[Path]:
    """Discover burst SAFE directories from explicit paths or collections.

    Explicit SAFE paths retain their input order.  A collection directory is
    searched recursively and its SAFE directories are returned in lexical
    order.  Duplicate paths are removed.
    """

    discovered: list[Path] = []
    seen: set[Path] = set()
    for raw in inputs:
        path = Path(raw).expanduser().resolve()
        candidates: list[Path]
        if _is_burst_safe(path):
            candidates = [path]
        elif path.is_dir():
            candidates = sorted(candidate for candidate in path.rglob("*.SAFE") if _is_burst_safe(candidate))
            if not candidates:
                raise BurstMergeError(
                    f"No burst SAFE directories found under {path}. "
                    "Expected directories containing measurement/*.tif(f) and annotation/*.xml."
                )
        else:
            raise BurstMergeError(f"Input is not a burst SAFE directory or collection: {path}")
        for candidate in candidates:
            if candidate not in seen:
                discovered.append(candidate)
                seen.add(candidate)
    if not discovered:
        raise BurstMergeError("At least one burst SAFE input is required")
    return discovered


def _load_numpy_tiff(path: Path):
    try:
        import numpy as np
        import tifffile
    except ImportError as exc:  # pragma: no cover - depends on installation
        raise BurstMergeError(
            "Sentinel-1 burst assembly requires numpy and tifffile. "
            "Install them with: pip install 'phidown[sentinel1]'"
        ) from exc
    try:
        array = tifffile.imread(str(path))
    except Exception as exc:
        raise BurstMergeError(f"Could not read measurement TIFF {path}: {exc}") from exc

    if np.iscomplexobj(array):
        components = np.stack((array.real, array.imag), axis=-1)
    elif array.ndim == 3 and array.shape[-1] == 2:
        components = array
    elif array.ndim == 3 and array.shape[0] == 2:
        components = np.moveaxis(array, 0, -1)
    else:
        raise BurstMergeError(
            f"Measurement {path} is not a two-component complex TIFF; got shape {array.shape}"
        )
    if components.ndim != 3 or components.shape[-1] != 2:
        raise BurstMergeError(f"Measurement {path} has unsupported shape {components.shape}")
    if not np.issubdtype(components.dtype, np.integer):
        components = np.rint(components)
    info = np.iinfo(np.int16)
    if np.any(components < info.min) or np.any(components > info.max):
        raise BurstMergeError(f"Measurement {path} contains values outside the int16 SLC range")
    return np.ascontiguousarray(components, dtype=np.int16)


def _measurement_gcps(group: Sequence[_BurstRecord]) -> list[tuple[float, float, float, float, float]]:
    """Return merged TIFF GCPs as (sample, line, x, y, z) tuples."""
    gcps: list[tuple[float, float, float, float, float]] = []
    offset = 0
    for record in group:
        grid = _child(_child(record.product, "geolocationGrid"), "geolocationGridPointList")
        for point in _children(grid, "geolocationGridPoint"):
            line_text = _first_text(point, "line")
            pixel_text = _first_text(point, "pixel")
            lon_text = _first_text(point, "longitude")
            lat_text = _first_text(point, "latitude")
            height_text = _first_text(point, "height") or "0"
            if any(value is None for value in (line_text, pixel_text, lon_text, lat_text)):
                continue
            assert line_text is not None and pixel_text is not None and lon_text is not None and lat_text is not None
            try:
                gcps.append(
                    (
                        float(pixel_text),
                        float(line_text) + offset,
                        float(lon_text),
                        float(lat_text),
                        float(height_text),
                    )
                )
            except ValueError:
                continue
        offset += record.lines
    return gcps


def _gdal_metadata(gcps: Sequence[tuple[float, float, float, float, float]]) -> str:
    """Create the GDAL TIFF metadata block used to expose GCPs."""
    projection = (
        'GEOGCS["WGS 84",DATUM["WGS_1984",'
        'SPHEROID["WGS 84",6378137,298.257223563]],'
        'PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433]]'
    )
    items = []
    for index, (sample, line, x, y, z) in enumerate(gcps):
        items.append(
            f'<Item name="GCP_{index}" sample="{sample:.12g}" line="{line:.12g}" '
            f'x="{x:.12g}" y="{y:.12g}" z="{z:.12g}" />'
        )
    items.append(f'<Item name="GCPProjection">{escape(projection)}</Item>')
    return "<GDALMetadata>" + "".join(items) + "</GDALMetadata>"


def _patch_s1_complex_int16_tags(path: Path, samples: int) -> None:
    """Mark tifffile's interleaved int16 storage as a complex-int16 TIFF.

    ``tifffile`` can write the exact I/Q byte stream but does not expose a
    complex-int16 NumPy dtype.  A 2-D int16 image with twice the width has the
    same bytes; changing ImageWidth, BitsPerSample, and SampleFormat makes it
    the TIFF representation required by the Sentinel-1 product specification.
    The IFD is patched in place so a multi-gigabyte SLC is never copied into
    Python memory a second time.
    """
    with path.open("r+b") as stream:
        header = stream.read(16)
        if len(header) < 8:
            raise BurstMergeError(f"Measurement TIFF is too short to patch: {path}")
        byte_order = header[:2]
        if byte_order == b"II":
            endian = "<"
        elif byte_order == b"MM":
            endian = ">"
        else:
            raise BurstMergeError(f"Unsupported TIFF byte order in {path}")
        magic = struct.unpack_from(f"{endian}H", header, 2)[0]
        if magic == 42:
            ifd_offset = struct.unpack_from(f"{endian}I", header, 4)[0]
            stream.seek(ifd_offset)
            count = struct.unpack(f"{endian}H", stream.read(2))[0]
            entry_size, count_size, value_offset = 12, 2, 8
            count_format = "I"
            field_size = 4
        elif magic == 43:
            if len(header) < 16:
                raise BurstMergeError(f"BigTIFF header is truncated: {path}")
            ifd_offset = struct.unpack_from(f"{endian}Q", header, 8)[0]
            stream.seek(ifd_offset)
            count = struct.unpack(f"{endian}Q", stream.read(8))[0]
            entry_size, count_size, value_offset = 20, 8, 12
            count_format = "Q"
            field_size = 8
        else:
            raise BurstMergeError(f"Unsupported TIFF variant in {path}: magic {magic}")

        found: set[int] = set()
        for index in range(int(count)):
            entry = int(ifd_offset) + count_size + index * entry_size
            stream.seek(entry)
            entry_bytes = stream.read(entry_size)
            if len(entry_bytes) != entry_size:
                raise BurstMergeError(f"Truncated TIFF IFD in {path}")
            tag = struct.unpack_from(f"{endian}H", entry_bytes, 0)[0]
            if tag == 256:
                stream.seek(entry + value_offset)
                stream.write(struct.pack(f"{endian}I", samples))
                found.add(tag)
            elif tag in {258, 339}:
                stream.seek(entry + 4)
                stream.write(struct.pack(f"{endian}{count_format}", 1))
                stream.write(b"\x00" * field_size)
                stream.seek(entry + value_offset)
                stream.write(struct.pack(f"{endian}H", 32 if tag == 258 else 5))
                found.add(tag)
        missing = {256, 258, 339} - found
        if missing:
            raise BurstMergeError(f"Could not find TIFF tags {sorted(missing)} in {path}")
        stream.flush()


def _write_measurement_stream(
    path: Path,
    data_inputs: Sequence[Path | Any],
    expected_shape: tuple[int, int, int],
    total_lines: int,
    gcps: Sequence[tuple[float, float, float, float, float]] = (),
) -> tuple[list[int], complex, float]:
    """Write one complex-int16 TIFF while loading one burst at a time."""
    try:
        import numpy as np
        import tifffile
    except ImportError as exc:  # pragma: no cover - depends on installation
        raise BurstMergeError(
            "Sentinel-1 burst assembly requires numpy and tifffile. "
            "Install them with: pip install 'phidown[sentinel1]'"
        ) from exc

    _lines, samples, components = expected_shape
    if components != 2:
        raise BurstMergeError(f"Expected I/Q data with two components; got {expected_shape}")
    sums = 0.0 + 0.0j
    sum_squared_magnitudes = 0.0
    nonzero_count = 0
    total_count = 0

    def rows():
        nonlocal sums, sum_squared_magnitudes, nonzero_count, total_count
        for data_input in data_inputs:
            array = _load_numpy_tiff(data_input) if isinstance(data_input, Path) else data_input
            if array.shape != expected_shape:
                raise BurstMergeError(f"Measurement has shape {array.shape}; expected {expected_shape}")
            values = array[..., 0].astype("float64") + 1j * array[..., 1].astype("float64")
            valid = np.any(array != 0, axis=-1)
            selected = values[valid]
            sums += selected.sum()
            sum_squared_magnitudes += np.square(np.abs(selected)).sum()
            nonzero_count += int(selected.size)
            total_count += int(values.size)
            for row in array:
                yield np.ascontiguousarray(row.reshape(samples * 2))

    try:
        extra_tags = [(42112, "s", len(_gdal_metadata(gcps)) + 1, _gdal_metadata(gcps), False)] if gcps else None
        storage_bytes = total_lines * samples * 4
        with tifffile.TiffWriter(str(path), bigtiff=bool(storage_bytes >= 4 * 1024**3)) as writer:
            writer.write(
                rows(),
                shape=(total_lines, samples * 2),
                dtype=np.int16,
                metadata=None,
                compression=None,
                rowsperstrip=1,
                photometric="minisblack",
                planarconfig="contig",
                description="Sentinel-1 assembled SLC complex-int16 measurement",
                extratags=extra_tags,
            )
        _patch_s1_complex_int16_tags(path, samples)
    except Exception as exc:
        raise BurstMergeError(f"Could not write assembled measurement {path}: {exc}") from exc

    try:
        with tifffile.TiffFile(str(path)) as tif:
            if len(tif.pages) != 1:
                raise BurstMergeError("Assembled measurement must contain exactly one TIFF page")
            page = tif.pages[0]
            offsets = tuple(int(offset) for offset in page.dataoffsets)
    except BurstMergeError:
        raise
    except Exception as exc:
        raise BurstMergeError(f"Could not inspect assembled TIFF {path}: {exc}") from exc
    if len(offsets) != total_lines:
        raise BurstMergeError(f"Assembled TIFF has {len(offsets)} row offsets for {total_lines} rows")

    if nonzero_count:
        mean = sums / nonzero_count
        variance = max(0.0, sum_squared_magnitudes / nonzero_count - float(abs(mean) ** 2))
    else:
        mean = 0.0 + 0.0j
        variance = 0.0
    return list(offsets), mean, float(np.sqrt(variance))


def _write_measurement(path: Path, array, gcps: Sequence[tuple[float, float, float, float, float]] = ()) -> list[int]:
    """Compatibility wrapper for writing an already-loaded burst array."""
    offsets, _, _ = _write_measurement_stream(path, [array], tuple(array.shape), array.shape[0], gcps)
    return offsets


def _validate_records(records: Sequence[_BurstRecord]) -> None:
    if not records:
        raise BurstMergeError("No burst records were found")
    platforms = {record.platform for record in records}
    modes = {record.mode for record in records}
    orbits = {record.absolute_orbit for record in records}
    if len(platforms) != 1:
        raise BurstMergeError(f"All bursts must come from the same platform; found {sorted(platforms)}")
    if len(modes) != 1:
        raise BurstMergeError(f"All bursts must use the same acquisition mode; found {sorted(modes)}")
    if len(orbits) != 1:
        raise BurstMergeError(f"All bursts must have the same absolute orbit; found {sorted(orbits)}")

    grouped: dict[tuple[str, str], list[_BurstRecord]] = {}
    for record in records:
        grouped.setdefault((record.swath, record.polarization), []).append(record)
    for (swath, polarization), group in grouped.items():
        group.sort(key=lambda item: (item.burst_id, item.start, str(item.data_path)))
        ids = [item.burst_id for item in group]
        if len(ids) != len(set(ids)):
            raise BurstMergeError(f"Duplicate burst IDs in {swath}/{polarization}: {ids}")
        expected = list(range(ids[0], ids[-1] + 1))
        if ids != expected:
            raise BurstMergeError(
                f"Bursts in {swath}/{polarization} must have consecutive IDs; found {ids}"
            )
        if len({item.lines for item in group}) != 1:
            raise BurstMergeError(f"All {swath}/{polarization} bursts must have the same line count")
        if len({item.samples for item in group}) != 1:
            raise BurstMergeError(f"All {swath}/{polarization} bursts must have the same sample count")

    # A dual-polarization SAFE must cover the same burst interval per swath.
    by_swath: dict[str, list[list[int]]] = {}
    for (swath, _polarization), group in grouped.items():
        by_swath.setdefault(swath, []).append([group[0].burst_id, group[-1].burst_id])
    for swath, ranges in by_swath.items():
        if len({tuple(item) for item in ranges}) != 1:
            raise BurstMergeError(f"Polarization groups in {swath} do not cover the same burst range: {ranges}")


def _group_records(records: Sequence[_BurstRecord]) -> list[tuple[tuple[str, str], list[_BurstRecord]]]:
    grouped: dict[tuple[str, str], list[_BurstRecord]] = {}
    for record in records:
        grouped.setdefault((record.swath, record.polarization), []).append(record)
    return [
        (key, sorted(value, key=lambda item: item.burst_id))
        for key, value in sorted(grouped.items())
    ]


def _as_product(root: ET.Element) -> ET.Element:
    if _local_name(root.tag) == "product" and _child(root, "swathTiming") is not None:
        return ET.fromstring(ET.tostring(root, encoding="utf-8"))
    if _local_name(root.tag) == "content":
        product = ET.Element("product")
        product.extend(ET.fromstring(ET.tostring(child, encoding="utf-8")) for child in list(root))
        return product
    product = ET.Element("product")
    product.extend(ET.fromstring(ET.tostring(child, encoding="utf-8")) for child in list(root))
    return product


def _replace_child(parent: ET.Element, old: ET.Element | None, new: ET.Element) -> None:
    if old is None:
        parent.append(new)
    else:
        index = list(parent).index(old)
        parent.remove(old)
        parent.insert(index, new)


def _merge_product(
    group: Sequence[_BurstRecord], image_number: int, byte_offsets: Sequence[int], total_lines: int, mean, std
) -> ET.Element:
    product = _as_product(group[0].product)
    first = group[0]
    start = min(record.start for record in group)
    stop = max(record.stop for record in group)
    _set_path_text(product, _format_time(start), "adsHeader", "startTime")
    _set_path_text(product, _format_time(stop), "adsHeader", "stopTime")
    _set_path_text(product, f"{image_number:03d}", "adsHeader", "imageNumber")
    _set_path_text(product, _format_time(start), "imageAnnotation", "imageInformation", "productFirstLineUtcTime")
    _set_path_text(product, _format_time(stop), "imageAnnotation", "imageInformation", "productLastLineUtcTime")
    _set_path_text(product, "Assembled", "imageAnnotation", "imageInformation", "productComposition")
    _set_path_text(product, "0", "imageAnnotation", "imageInformation", "sliceNumber")
    image_info = _child(_child(product, "imageAnnotation"), "imageInformation")
    if image_info is not None:
        image_info.attrib.pop("numberOfLines", None)
    _set_path_text(product, total_lines, "imageAnnotation", "imageInformation", "numberOfLines")
    _set_path_text(product, f"{mean.real:.6e}", "imageAnnotation", "imageInformation", "imageStatistics", "outputDataMean", "re")
    _set_path_text(product, f"{mean.imag:.6e}", "imageAnnotation", "imageInformation", "imageStatistics", "outputDataMean", "im")
    _set_path_text(product, f"{std.real:.6e}", "imageAnnotation", "imageInformation", "imageStatistics", "outputDataStdDev", "re")
    _set_path_text(product, f"{std.imag:.6e}", "imageAnnotation", "imageInformation", "imageStatistics", "outputDataStdDev", "im")

    timing = _child(product, "swathTiming")
    if timing is None:
        timing = ET.SubElement(product, "swathTiming")
    _set_text(_child(timing, "linesPerBurst"), first.lines)
    _set_text(_child(timing, "samplesPerBurst"), first.samples)
    burst_list = ET.Element("burstList", {"count": str(len(group))})
    for record, offset in zip(group, byte_offsets):
        source_list = _child(_child(record.product, "swathTiming"), "burstList")
        source_burst = _children(source_list, "burst")[0]
        burst = ET.fromstring(ET.tostring(source_burst, encoding="utf-8"))
        byte_offset = _first_descendant(burst, "byteOffset")
        if byte_offset is None:
            byte_offset = ET.SubElement(burst, "byteOffset")
        _set_text(byte_offset, offset)
        burst_list.append(burst)
    _replace_child(timing, _child(timing, "burstList"), burst_list)

    geo = _child(product, "geolocationGrid")
    if geo is not None:
        source_grid = _child(geo, "geolocationGridPointList")
        merged_grid = ET.Element("geolocationGridPointList")
        for record, offset in zip(group, [sum(item.lines for item in group[:index]) for index in range(len(group))]):
            source_geo = _child(_child(record.product, "geolocationGrid"), "geolocationGridPointList")
            for point in _children(source_geo, "geolocationGridPoint"):
                copy = ET.fromstring(ET.tostring(point, encoding="utf-8"))
                line = _first_descendant(copy, "line")
                if line is not None and line.text:
                    try:
                        value = float(line.text) + offset
                        _set_text(line, int(value) if value.is_integer() else value)
                    except ValueError:
                        pass
                merged_grid.append(copy)
        merged_grid.set("count", str(len(merged_grid)))
        _replace_child(geo, source_grid, merged_grid)

    # Keep the first source's non-line-dependent lists.  The burst timing and
    # geolocation lists above are the records that change row-by-row; the
    # remaining lists are valid for the source SLC and are Include components.
    _set_path_text(product, _format_time(start), "adsHeader", "startTime")
    _set_path_text(product, _format_time(stop), "adsHeader", "stopTime")
    return product


def _merge_auxiliary(
    group: Sequence[_BurstRecord],
    kind: str,
    line_offsets: Sequence[int],
    start: datetime,
    stop: datetime,
    image_number: int | None = None,
) -> ET.Element | None:
    component_pairs = [
        (component, offset)
        for record, offset in zip(group, line_offsets)
        if (component := getattr(record, kind)) is not None
    ]
    if not component_pairs:
        return None
    components = [component for component, _ in component_pairs]
    output = ET.fromstring(ET.tostring(components[0], encoding="utf-8"))
    _set_path_text(output, _format_time(start), "adsHeader", "startTime")
    _set_path_text(output, _format_time(stop), "adsHeader", "stopTime")
    if image_number is not None:
        _set_path_text(output, f"{image_number:03d}", "adsHeader", "imageNumber")

    lists = [candidate for candidate in output.iter() if _local_name(candidate.tag).endswith("VectorList")]
    if not lists:
        return output
    for output_list in lists:
        list_name = _local_name(output_list.tag)
        merged: list[ET.Element] = []
        seen: set[bytes] = set()
        for component, offset in component_pairs:
            input_list = next(
                (candidate for candidate in component.iter() if _local_name(candidate.tag) == list_name), None
            )
            if input_list is None:
                continue
            for vector in list(input_list):
                copy = ET.fromstring(ET.tostring(vector, encoding="utf-8"))
                if kind == "noise" and list_name == "noiseAzimuthVectorList":
                    if not _transform_noise_azimuth_vector(copy, offset=offset):
                        continue
                else:
                    line = _first_descendant(copy, "line")
                    if line is not None and line.text:
                        try:
                            value = float(line.text) + offset
                            _set_text(line, int(value) if value.is_integer() else value)
                        except ValueError:
                            pass
                fingerprint = ET.tostring(copy, encoding="utf-8")
                if fingerprint not in seen:
                    merged.append(copy)
                    seen.add(fingerprint)
        for child in list(output_list):
            output_list.remove(child)
        for child in merged:
            output_list.append(child)
        output_list.set("count", str(len(merged)))
    return output


def _polygon_hull(points: Iterable[tuple[float, float]]) -> list[tuple[float, float]]:
    unique = sorted(set(points))
    if len(unique) <= 2:
        return unique

    def cross(origin, first, second):
        return (first[0] - origin[0]) * (second[1] - origin[1]) - (first[1] - origin[1]) * (second[0] - origin[0])

    lower: list[tuple[float, float]] = []
    for point in unique:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], point) <= 0:
            lower.pop()
        lower.append(point)
    upper: list[tuple[float, float]] = []
    for point in reversed(unique):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], point) <= 0:
            upper.pop()
        upper.append(point)
    return lower[:-1] + upper[:-1]


def _group_footprint(group: Sequence[_BurstRecord]) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    for record in group:
        grid = _child(_child(record.product, "geolocationGrid"), "geolocationGridPointList")
        for point in _children(grid, "geolocationGridPoint"):
            lon = _first_text(point, "longitude")
            lat = _first_text(point, "latitude")
            if lon is not None and lat is not None:
                try:
                    points.append((float(lon), float(lat)))
                except ValueError:
                    pass
    return _polygon_hull(points)


def _all_footprint(records: Sequence[_BurstRecord]) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    for _, group in _group_records(records):
        points.extend(_group_footprint(group))
    return _polygon_hull(points)


def _footprint_string(points: Sequence[tuple[float, float]]) -> str:
    return " ".join(f"{lon:.6f},{lat:.6f}" for lon, lat in points)


def _safe_product_name(records: Sequence[_BurstRecord], output_name: str | None) -> str:
    if output_name:
        return output_name if output_name.upper().endswith(".SAFE") else f"{output_name}.SAFE"
    first = records[0]
    pols = sorted({record.polarization for record in records})
    pol_code = {
        ("HH",): "SH",
        ("VV",): "SV",
        ("VH",): "VH",
        ("HV",): "HV",
        ("HH", "HV"): "DH",
        ("VH", "VV"): "DV",
    }.get(tuple(pols), "SV")
    start = min(record.start for record in records).strftime("%Y%m%dT%H%M%S")
    stop = max(record.stop for record in records).strftime("%Y%m%dT%H%M%S")
    orbit = f"{first.absolute_orbit:06d}"
    datatake = first.datatake_id or "000000"
    return f"{first.platform}_{first.mode}_SLC__1S{pol_code}_{start}_{stop}_{orbit}_{datatake}_0000.SAFE"


def _output_stem(record: _BurstRecord, start: datetime, stop: datetime, image_number: int) -> str:
    return (
        f"{record.platform.lower()}-{record.swath.lower()}-slc-{record.polarization.lower()}-"
        f"{start.strftime('%Y%m%dt%H%M%S')}-{stop.strftime('%Y%m%dt%H%M%S')}-"
        f"{record.absolute_orbit:06d}-{record.datatake_id or '000000'}-{image_number:03d}"
    )


def _make_output_file(path: Path, kind: str) -> _OutputFile:
    mappings = {
        "product": ("s1Level1ProductSchema", "Metadata Unit"),
        "noise": ("s1Level1NoiseSchema", "Metadata Unit"),
        "calibration": ("s1Level1CalibrationSchema", "Metadata Unit"),
        "rfi": ("s1Level1RfiSchema", "Metadata Unit"),
        "measurement": ("s1Level1MeasurementSchema", "Measurement Data Unit"),
        "mapoverlay": ("s1Level1MapOverlaySchema", "Metadata Unit"),
        "productpreview": ("s1Level1ProductPreviewSchema", "Metadata Unit"),
    }
    rep_id, unit_type = mappings[kind]
    if kind == "mapoverlay":
        data_id = "mapoverlay"
    elif kind == "productpreview":
        data_id = "productpreview"
    else:
        stem_id = path.stem.replace("-", "")
        prefix = "product" if kind == "product" else kind
        data_id = f"{prefix}{stem_id}"
    metadata_id = f"{data_id}Annotation"
    return _OutputFile(path, kind, rep_id, unit_type, data_id, metadata_id)


def _md5(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _copy_template_metadata(template: ET.Element | None, output: ET.Element, start: datetime, stop: datetime, footprint: str) -> None:
    if template is None:
        return
    metadata_section = ET.SubElement(output, "metadataSection")
    keep_ids = {
        "processing",
        "platform",
        "measurementOrbitReference",
        "generalProductInformation",
        "acquisitionPeriod",
        "measurementFrameSet",
        "s1Level1ProductSchema",
        "s1Level1NoiseSchema",
        "s1Level1RfiSchema",
        "s1Level1CalibrationSchema",
        "s1ObjectTypesSchema",
        "s1Level1MeasurementSchema",
    }
    for candidate in _descendants(template, "metadataObject"):
        object_id = candidate.get("ID")
        if object_id in keep_ids:
            clone = ET.fromstring(ET.tostring(candidate, encoding="utf-8"))
            if object_id == "acquisitionPeriod":
                _set_path_text(clone, _format_time(start), "metadataWrap", "xmlData", "acquisitionPeriod", "startTime")
                _set_path_text(clone, _format_time(stop), "metadataWrap", "xmlData", "acquisitionPeriod", "stopTime")
            if object_id == "measurementFrameSet":
                coordinates = _first_descendant(clone, "coordinates")
                _set_text(coordinates, footprint)
            metadata_section.append(clone)
    return


def _create_manifest(
    safe_path: Path,
    template: ET.Element | None,
    files: Sequence[_OutputFile],
    start: datetime,
    stop: datetime,
    footprint: str,
) -> None:
    xfdu_ns = "urn:ccsds:schema:xfdu:1"
    ET.register_namespace("xfdu", xfdu_ns)
    root = ET.Element(
        f"{{{xfdu_ns}}}XFDU",
        {"version": "esa/safe/sentinel-1.0/sentinel-1/sar/level-1/slc/standard/iwdp"},
    )
    information_map = ET.SubElement(root, "informationPackageMap")
    parent = ET.SubElement(
        information_map,
        f"{{{xfdu_ns}}}contentUnit",
        {
            "unitType": "SAFE Archive Information Package",
            "textInfo": "Sentinel-1 Level-1 SLC Product",
            "dmdID": "acquisitionPeriod platform generalProductInformation measurementOrbitReference measurementFrameSet",
            "pdiID": "processing",
        },
    )
    metadata_files = [file for file in files if file.kind in {"product", "noise", "calibration", "rfi"}]
    for file in files:
        attrs = {"unitType": file.unit_type, "repID": file.rep_id}
        if file.kind == "measurement":
            attrs["dmdID"] = " ".join(item.metadata_id for item in metadata_files)
        unit = ET.SubElement(parent, f"{{{xfdu_ns}}}contentUnit", attrs)
        ET.SubElement(unit, "dataObjectPointer", {"dataObjectID": file.data_id})

    _copy_template_metadata(template, root, start, stop, footprint)
    metadata_section = _child(root, "metadataSection")
    if metadata_section is None:
        metadata_section = ET.SubElement(root, "metadataSection")

    for file in files:
        metadata_object = ET.SubElement(
            metadata_section,
            "metadataObject",
            {"ID": file.metadata_id, "classification": "DESCRIPTION", "category": "DMD"},
        )
        ET.SubElement(metadata_object, "dataObjectPointer", {"dataObjectID": file.data_id})

    data_section = ET.SubElement(root, "dataObjectSection")
    for file in files:
        relative = file.path.relative_to(safe_path).as_posix()
        byte_stream = ET.SubElement(
            data_section,
            "dataObject",
            {"ID": file.data_id, "repID": file.rep_id},
        )
        stream = ET.SubElement(
            byte_stream,
            "byteStream",
            {
                "mimeType": "text/xml" if file.path.suffix.lower() in {".xml", ".kml", ".html"} else "application/octet-stream",
                "size": str(file.path.stat().st_size),
            },
        )
        ET.SubElement(
            stream,
            "fileLocation",
            {"locatorType": "URL", "href": f"./{relative}"},
        )
        checksum = ET.SubElement(stream, "checksum", {"checksumName": "MD5"})
        checksum.text = _md5(file.path)

    ET.indent(root, space="  ")
    ET.ElementTree(root).write(
        safe_path / "manifest.safe", encoding="utf-8", xml_declaration=True
    )


def _write_preview(safe_path: Path, footprint: Sequence[tuple[float, float]], product_name: str) -> None:
    """Write small human-readable preview files without inventing a quicklook."""

    preview = safe_path / "preview"
    preview.mkdir(parents=True, exist_ok=True)
    coords = " ".join(f"{lon:.6f},{lat:.6f},0" for lon, lat in footprint)
    if footprint and footprint[0] != footprint[-1]:
        coords += f" {footprint[0][0]:.6f},{footprint[0][1]:.6f},0"
    kml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<kml xmlns="http://www.opengis.net/kml/2.2"><Document>'
        f"<name>{product_name}</name><Placemark><name>Assembled footprint</name>"
        f"<Polygon><outerBoundaryIs><LinearRing><coordinates>{coords}</coordinates>"
        "</LinearRing></outerBoundaryIs></Polygon></Placemark></Document></kml>"
    )
    (preview / "map-overlay.kml").write_text(kml, encoding="utf-8")
    html = (
        "<!doctype html><html><head><meta charset=\"utf-8\"><title>"
        + product_name
        + "</title></head><body><h1>"
        + product_name
        + "</h1><p>Assembled Sentinel-1 SLC SAFE. See <a href=\"../manifest.safe\">manifest.safe</a>.</p>"
        "</body></html>"
    )
    (preview / "product-preview.html").write_text(html, encoding="utf-8")


def _extract_burst_archive(archive: Path, destination: Path) -> Path:
    """Extract a downloaded burst ZIP without allowing path traversal."""
    destination.mkdir(parents=True, exist_ok=True)
    root = destination.resolve()
    try:
        with zipfile.ZipFile(archive) as zipped:
            for member in zipped.infolist():
                if member.is_dir():
                    continue
                target = (destination / member.filename).resolve()
                try:
                    inside = os.path.commonpath((str(root), str(target))) == str(root)
                except ValueError:
                    inside = False
                if not inside:
                    raise BurstMergeError(f"Unsafe path in burst archive {archive}: {member.filename!r}")
                target.parent.mkdir(parents=True, exist_ok=True)
                with zipped.open(member) as source, target.open("wb") as output:
                    shutil.copyfileobj(source, output)
    except BurstMergeError:
        raise
    except (OSError, ValueError, zipfile.BadZipFile, RuntimeError) as exc:
        raise BurstMergeError(f"Could not extract burst archive {archive}: {exc}") from exc
    return destination


def merge_burst_safes(
    inputs: Iterable[str | os.PathLike[str]],
    output_dir: str | os.PathLike[str] = ".",
    *,
    output_name: str | None = None,
    overwrite: bool = False,
) -> Path:
    """Merge downloaded burst SAFEs or burst ZIP archives into one SAFE."""
    input_paths = [Path(raw).expanduser().resolve() for raw in inputs]
    archives = [path for path in input_paths if path.suffix.lower() == ".zip"]
    if not archives:
        return _merge_burst_safes_without_archives(
            input_paths, output_dir, output_name=output_name, overwrite=overwrite
        )

    resolved_output = Path(output_dir).expanduser().resolve()
    resolved_output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".phidown-burst-input-", dir=str(resolved_output)) as temporary:
        extracted_inputs = [path for path in input_paths if path not in archives]
        for index, archive in enumerate(archives):
            extracted_inputs.append(_extract_burst_archive(archive, Path(temporary) / f"archive-{index}"))
        return _merge_burst_safes_without_archives(
            extracted_inputs, resolved_output, output_name=output_name, overwrite=overwrite
        )


def _merge_burst_safes_without_archives(
    inputs: Iterable[str | os.PathLike[str]],
    output_dir: str | os.PathLike[str] = ".",
    *,
    output_name: str | None = None,
    overwrite: bool = False,
) -> Path:
    """Merge downloaded single-burst SAFEs into one assembled SAFE.

    Args:
        inputs: Burst SAFE directories or directories containing them.
        output_dir: Directory in which the assembled ``*.SAFE`` is created.
        output_name: Optional output SAFE name. ``.SAFE`` is appended when
            omitted. Without it, a Sentinel-1 product name is generated.
        overwrite: Replace an existing output SAFE.

    Returns:
        The path to the assembled SAFE directory.

    Raises:
        BurstMergeError: If the inputs are incomplete, incompatible, or
            malformed.
    """

    input_paths = [Path(raw).expanduser().resolve() for raw in inputs]
    json_inputs = [path for path in input_paths if path.is_file() and path.suffix.lower() == ".json"]
    safe_inputs = [path for path in input_paths if path not in json_inputs]
    safe_paths = discover_burst_safes(safe_inputs) if safe_inputs else []
    records: list[_BurstRecord] = []
    for tree_path in json_inputs:
        records.extend(_records_from_tree(tree_path))
    for safe_path in safe_paths:
        measurements = sorted(
            file for file in (safe_path / "measurement").iterdir() if file.is_file() and file.suffix.lower() in _TIFF_SUFFIXES
        )
        if not measurements:
            raise BurstMergeError(f"No measurement TIFF found in {safe_path}")
        for measurement in measurements:
            records.append(_record_from_paths(safe_path, measurement))
    _validate_records(records)

    output_root = Path(output_dir).expanduser().resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    final_name = _safe_product_name(records, output_name)
    final_path = output_root / final_name
    if final_path.exists() and not overwrite:
        raise BurstMergeError(f"Output SAFE already exists: {final_path}")

    work_parent = Path(tempfile.mkdtemp(prefix=".phidown-burst-", dir=str(output_root)))
    work_safe = work_parent / final_name
    files: list[_OutputFile] = []
    try:
        (work_safe / "measurement").mkdir(parents=True)
        (work_safe / "annotation" / "calibration").mkdir(parents=True)
        grouped = _group_records(records)
        image_number = 0
        for (_swath, _polarization), group in grouped:
            image_number += 1
            expected_shape = (group[0].lines, group[0].samples, 2)
            total_lines = group[0].lines * len(group)
            start = min(record.start for record in group)
            stop = max(record.stop for record in group)
            stem = _output_stem(group[0], start, stop, image_number)
            measurement_path = work_safe / "measurement" / f"{stem}.tiff"
            byte_offsets, mean, std = _write_measurement_stream(
                measurement_path,
                [record.data_path for record in group],
                expected_shape,
                total_lines,
                _measurement_gcps(group),
            )
            line_offsets = [sum(record.lines for record in group[:index]) for index in range(len(group))]
            product = _merge_product(group, image_number, [byte_offsets[index * group[0].lines] for index in range(len(group))], total_lines, mean, std)
            product_path = work_safe / "annotation" / f"{stem}.xml"
            ET.indent(product, space="  ")
            ET.ElementTree(product).write(product_path, encoding="utf-8", xml_declaration=True)
            files.extend([_make_output_file(product_path, "product"), _make_output_file(measurement_path, "measurement")])

            for kind in ("noise", "calibration", "rfi"):
                aux = _merge_auxiliary(group, kind, line_offsets, start, stop, image_number=image_number)
                if aux is None:
                    continue
                directory = "annotation/rfi" if kind == "rfi" else "annotation/calibration"
                (work_safe / directory).mkdir(parents=True, exist_ok=True)
                aux_path = work_safe / directory / f"{kind}-{stem}.xml"
                ET.indent(aux, space="  ")
                ET.ElementTree(aux).write(aux_path, encoding="utf-8", xml_declaration=True)
                files.append(_make_output_file(aux_path, kind))

        # Prefer the IPF-matched support directory from an input SAFE; the
        # bundled Sentinel-1 schemas cover the common burst-extractor output.
        support_source = next((path / "support" for path in safe_paths if (path / "support").is_dir()), None)
        if support_source is None:
            bundled_support = Path(__file__).parent / "data" / "sentinel1_support"
            support_source = bundled_support if bundled_support.is_dir() else None
        if support_source is not None:
            shutil.copytree(support_source, work_safe / "support", dirs_exist_ok=True)

        footprint_points = _all_footprint(records)
        footprint = _footprint_string(footprint_points)
        template = records[0].manifest
        _write_preview(work_safe, footprint_points, final_name)
        files.extend(
            [
                _make_output_file(work_safe / "preview" / "map-overlay.kml", "mapoverlay"),
                _make_output_file(work_safe / "preview" / "product-preview.html", "productpreview"),
            ]
        )
        _create_manifest(
            work_safe,
            template,
            files,
            min(record.start for record in records),
            max(record.stop for record in records),
            footprint,
        )

        # The product name ends in a four-character CRC in the normal SAFE
        # convention.  Compute it after manifest creation, then rename the
        # root; internal paths are relative and do not need rewriting.
        crc = _crc16(work_safe / "manifest.safe")
        actual_name = re.sub(r"_0000\.SAFE$", f"_{crc}.SAFE", final_name, flags=re.IGNORECASE)
        actual_path = output_root / actual_name
        if actual_path.exists() and not overwrite:
            raise BurstMergeError(f"Output SAFE already exists: {actual_path}")
        if actual_path.exists():
            shutil.rmtree(actual_path)
        work_safe.rename(actual_path)
        return actual_path
    except Exception:
        shutil.rmtree(work_parent, ignore_errors=True)
        raise
    finally:
        if work_parent.exists():
            shutil.rmtree(work_parent, ignore_errors=True)


def _crc16(path: Path) -> str:
    """Calculate the CRC-16/CCITT used in Sentinel-1 SAFE identifiers."""

    crc = 0xFFFF
    with path.open("rb") as stream:
        for byte in iter(lambda: stream.read(1), b""):
            crc ^= byte[0] << 8
            for _ in range(8):
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return f"{crc:04X}"


__all__ = ["BurstMergeError", "discover_burst_safes", "merge_burst_safes"]
