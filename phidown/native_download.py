"""Native resumable download helpers for S3-backed product transfers."""

from __future__ import annotations

import configparser
import importlib
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

from tqdm import tqdm

from .download_state import DownloadStateStore, default_state_file
from .s5cmd_utils import ensure_s5cmd_config

logger = logging.getLogger(__name__)


@dataclass
class S3ObjectMeta:
    bucket: str
    key: str
    size: int
    etag: Optional[str]


@dataclass
class NativeDownloadResult:
    status: str
    output_path: str
    object_count: int
    bytes_transferred: int


def _import_boto3_modules():
    """Import boto3/botocore lazily so plain module import stays lightweight."""
    boto3 = importlib.import_module("boto3")
    botocore_config = importlib.import_module("botocore.config")
    return boto3, botocore_config.Config


def _parse_bool(value: str, default: bool = True) -> bool:
    text = str(value).strip("'\"").lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return default


def _read_s3_config(config_file: str) -> Dict[str, Any]:
    config = configparser.ConfigParser()
    if not os.path.exists(config_file):
        raise FileNotFoundError(f"Configuration file {config_file} not found")
    config.read(config_file)
    if "default" not in config:
        raise ValueError(f"Configuration file {config_file} is missing a [default] section")

    default = config["default"]
    host_base = default.get("host_base", "eodata.dataspace.copernicus.eu").strip("'\"")
    use_https = _parse_bool(default.get("use_https", "true"))
    endpoint_url = f"{'https' if use_https else 'http'}://{host_base}"
    return {
        "aws_access_key_id": default.get("aws_access_key_id", "").strip("'\""),
        "aws_secret_access_key": default.get("aws_secret_access_key", "").strip("'\""),
        "region_name": default.get("aws_region", "us-east-1").strip("'\""),
        "endpoint_url": endpoint_url,
    }


def _build_s3_client(
    config_file: str,
    *,
    connect_timeout: float,
    read_timeout: Optional[float],
):
    boto3, Config = _import_boto3_modules()
    cfg = _read_s3_config(config_file)
    timeout_value = float(connect_timeout) if read_timeout is None else float(read_timeout)
    return boto3.client(
        "s3",
        aws_access_key_id=cfg["aws_access_key_id"],
        aws_secret_access_key=cfg["aws_secret_access_key"],
        region_name=cfg["region_name"],
        endpoint_url=cfg["endpoint_url"],
        config=Config(
            signature_version="s3v4",
            connect_timeout=float(connect_timeout),
            read_timeout=timeout_value,
            retries={"max_attempts": 0},
            s3={"addressing_style": "path"},
        ),
    )


def _parse_cdse_s3_path(s3_path: str) -> Tuple[str, str]:
    if not s3_path.startswith("/eodata/"):
        raise ValueError(f"S3 path must start with /eodata/, got: {s3_path}")
    trimmed = s3_path.lstrip("/")
    bucket, _, key = trimmed.partition("/")
    if not bucket or not key:
        raise ValueError(f"Invalid CDSE S3 path: {s3_path}")
    return bucket, key.rstrip("/")


def _ensure_parent(path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)


def _normalize_etag(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    return str(value).strip('"')


def _object_state_map(record: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    raw = record.get("objects")
    return raw if isinstance(raw, dict) else {}


def _build_record(
    *,
    existing: Optional[Dict[str, Any]],
    status: str,
    source_path: str,
    output_path: str,
    download_all: bool,
    object_states: Dict[str, Dict[str, Any]],
    attempts: Optional[int] = None,
    error: Optional[str] = None,
) -> Dict[str, Any]:
    prior = existing or {}
    record: Dict[str, Any] = {
        "status": status,
        "source_path": source_path,
        "output_path": output_path,
        "download_all": download_all,
        "objects": object_states,
    }
    if attempts is not None:
        record["attempts"] = attempts
    elif "attempts" in prior:
        record["attempts"] = prior["attempts"]
    if error is not None:
        record["error"] = error
    elif status != "success" and "error" in prior:
        record["error"] = prior["error"]
    completed = sum(1 for obj in object_states.values() if obj.get("status") == "success")
    record["completed_objects"] = completed
    record["object_count"] = len(object_states)
    record["bytes_transferred"] = sum(int(obj.get("completed_bytes", 0)) for obj in object_states.values())
    return record


def _list_objects(client, bucket: str, key: str, download_all: bool) -> List[S3ObjectMeta]:
    if download_all:
        prefix = key if key.endswith("/") else f"{key}/"
        paginator = client.get_paginator("list_objects_v2")
        objects: List[S3ObjectMeta] = []
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for item in page.get("Contents", []):
                objects.append(
                    S3ObjectMeta(
                        bucket=bucket,
                        key=item["Key"],
                        size=int(item["Size"]),
                        etag=_normalize_etag(item.get("ETag")),
                    )
                )
        if not objects:
            raise FileNotFoundError(f"No objects found under {bucket}/{prefix}")
        return objects

    head = client.head_object(Bucket=bucket, Key=key)
    return [
        S3ObjectMeta(
            bucket=bucket,
            key=key,
            size=int(head["ContentLength"]),
            etag=_normalize_etag(head.get("ETag")),
        )
    ]


def _download_root(output_dir: str, key: str, download_all: bool) -> str:
    if download_all:
        return os.path.join(output_dir, os.path.basename(key.rstrip("/")))
    return os.path.join(output_dir, os.path.basename(key.rstrip("/")))


def _object_output_path(root_output_path: str, key: str, prefix: str, download_all: bool) -> str:
    if download_all:
        relative = key[len(prefix):].lstrip("/")
        return os.path.join(root_output_path, relative)
    return root_output_path


def _existing_object_progress(
    final_path: str,
    temp_path: str,
    meta: S3ObjectMeta,
    object_state: Optional[Dict[str, Any]],
    download_all: bool,
) -> Tuple[str, int]:
    recorded_etag = _normalize_etag(object_state.get("etag")) if object_state else None
    if object_state and recorded_etag and meta.etag and recorded_etag != meta.etag:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        if os.path.isfile(final_path):
            os.remove(final_path)

    if os.path.isfile(final_path):
        final_size = os.path.getsize(final_path)
        trust_existing_final = download_all or object_state is not None
        if trust_existing_final and final_size == meta.size:
            return "success", meta.size
        if trust_existing_final:
            os.remove(final_path)

    if os.path.isfile(temp_path):
        partial_size = os.path.getsize(temp_path)
        if partial_size > meta.size:
            os.remove(temp_path)
            return "pending", 0
        if partial_size == meta.size:
            os.replace(temp_path, final_path)
            return "success", meta.size
        return "partial", partial_size

    return "pending", 0


def _stream_body_to_file(body, path: str, mode: str, progress: Optional[tqdm]) -> int:
    written = 0
    with open(path, mode) as handle:
        for chunk in body.iter_chunks(chunk_size=1024 * 1024):
            if not chunk:
                continue
            handle.write(chunk)
            written += len(chunk)
            if progress is not None:
                progress.update(len(chunk))
    return written


def download_s3_resumable(
    *,
    s3_path: str,
    output_dir: str,
    config_file: str,
    download_all: bool = True,
    state_file: Optional[str] = None,
    state_item_id: Optional[str] = None,
    connect_timeout: float = 30.0,
    read_timeout: Optional[float] = None,
    show_progress: bool = True,
    attempts: int = 1,
    persist_state: bool = True,
    reset_config: bool = False,
) -> NativeDownloadResult:
    """Download a product/object using native ranged S3 reads."""
    abs_output_dir = os.path.abspath(output_dir)
    os.makedirs(abs_output_dir, exist_ok=True)

    bucket, key = _parse_cdse_s3_path(s3_path)
    root_output_path = _download_root(abs_output_dir, key, download_all)
    item_id = state_item_id or f"s3:{s3_path}"

    ensure_s5cmd_config(config_file, reset=reset_config)

    client = _build_s3_client(
        config_file,
        connect_timeout=connect_timeout,
        read_timeout=read_timeout,
    )
    objects = _list_objects(client, bucket, key, download_all)
    prefix = key if key.endswith("/") else f"{key}/"

    state_store = None
    existing: Dict[str, Any] = {}
    if persist_state:
        resolved_state_file = state_file or default_state_file(abs_output_dir)
        state_store = DownloadStateStore(resolved_state_file)
        existing = state_store.get(item_id) or {}
    object_states = _object_state_map(existing)

    initial_bytes = 0
    for meta in objects:
        final_path = _object_output_path(root_output_path, meta.key, prefix, download_all)
        temp_path = f"{final_path}.part"
        status, completed_bytes = _existing_object_progress(
            final_path,
            temp_path,
            meta,
            object_states.get(meta.key),
            download_all,
        )
        object_states[meta.key] = {
            "status": status,
            "output_path": final_path,
            "temp_path": temp_path,
            "etag": meta.etag,
            "size": meta.size,
            "completed_bytes": completed_bytes,
        }
        initial_bytes += completed_bytes

    if all(state.get("status") == "success" for state in object_states.values()):
        record = _build_record(
            existing=existing,
            status="success",
            source_path=s3_path,
            output_path=root_output_path,
            download_all=download_all,
            object_states=object_states,
        )
        if state_store is not None:
            state_store.set(item_id, record)
        return NativeDownloadResult(
            status="skipped",
            output_path=root_output_path,
            object_count=len(objects),
            bytes_transferred=0,
        )

    record = _build_record(
        existing=existing,
        status="in_progress",
        source_path=s3_path,
        output_path=root_output_path,
        download_all=download_all,
        object_states=object_states,
        attempts=attempts,
    )
    if state_store is not None:
        state_store.set(item_id, record)

    total_size = sum(meta.size for meta in objects)
    progress = None
    bytes_written = 0
    if show_progress and total_size > 0:
        progress = tqdm(
            total=total_size,
            initial=initial_bytes,
            unit="B",
            unit_scale=True,
            unit_divisor=1024,
            desc="Downloading",
        )

    try:
        for meta in objects:
            state = object_states[meta.key]
            if state["status"] == "success":
                continue

            final_path = state["output_path"]
            temp_path = state["temp_path"]
            completed_bytes = int(state.get("completed_bytes", 0))
            _ensure_parent(final_path)

            if completed_bytes < 0 or completed_bytes > meta.size:
                completed_bytes = 0
                if os.path.exists(temp_path):
                    os.remove(temp_path)

            request_kwargs = {"Bucket": meta.bucket, "Key": meta.key}
            mode = "wb"
            if completed_bytes > 0:
                request_kwargs["Range"] = f"bytes={completed_bytes}-"
                mode = "ab"

            response = client.get_object(**request_kwargs)
            status_code = response.get("ResponseMetadata", {}).get("HTTPStatusCode")
            if completed_bytes > 0 and status_code != 206:
                completed_bytes = 0
                mode = "wb"
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                response = client.get_object(Bucket=meta.bucket, Key=meta.key)

            chunk_bytes = _stream_body_to_file(response["Body"], temp_path, mode, progress)
            bytes_written += chunk_bytes
            final_size = os.path.getsize(temp_path)
            if final_size != meta.size:
                state["completed_bytes"] = final_size
                state["status"] = "partial"
                record = _build_record(
                    existing=record,
                    status="failed",
                    source_path=s3_path,
                    output_path=root_output_path,
                    download_all=download_all,
                    object_states=object_states,
                    attempts=attempts,
                    error=f"Incomplete object download for {meta.key}: {final_size}/{meta.size} bytes",
                )
                if state_store is not None:
                    state_store.set(item_id, record)
                raise RuntimeError(record["error"])

            os.replace(temp_path, final_path)
            state["completed_bytes"] = meta.size
            state["status"] = "success"
            record = _build_record(
                existing=record,
                status="in_progress",
                source_path=s3_path,
                output_path=root_output_path,
                download_all=download_all,
                object_states=object_states,
                attempts=attempts,
            )
            if state_store is not None:
                state_store.set(item_id, record)

        record = _build_record(
            existing=record,
            status="success",
            source_path=s3_path,
            output_path=root_output_path,
            download_all=download_all,
            object_states=object_states,
            attempts=attempts,
        )
        if state_store is not None:
            state_store.set(item_id, record)
        return NativeDownloadResult(
            status="downloaded",
            output_path=root_output_path,
            object_count=len(objects),
            bytes_transferred=bytes_written,
        )
    except Exception as exc:
        record = _build_record(
            existing=record,
            status="failed",
            source_path=s3_path,
            output_path=root_output_path,
            download_all=download_all,
            object_states=object_states,
            attempts=attempts,
            error=str(exc),
        )
        if state_store is not None:
            state_store.set(item_id, record)
        raise
    finally:
        if progress is not None:
            progress.close()
