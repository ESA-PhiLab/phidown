"""PhiSat-2 INSULA search and download helpers."""

from __future__ import annotations

import configparser
from dataclasses import dataclass
import getpass
import logging
import os
from pathlib import Path
import random
import re
import time
import typing
import zipfile

import pandas as pd
import requests
from tqdm import tqdm

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT_SECONDS = 30
DEFAULT_CONNECT_TIMEOUT_SECONDS = 30.0
DEFAULT_READ_TIMEOUT_SECONDS = 900.0
PHISAT2_SECTION = "phisat2"
DEFAULT_BASE_URL = "https://phisat2.insula.earth"
DEFAULT_API_BASE = f"{DEFAULT_BASE_URL}/secure/api/v2.0"
DEFAULT_AUTHORIZATION_ENDPOINT = (
    "https://identity.insula.earth/realms/phisat2/protocol/openid-connect/auth"
)
DEFAULT_TOKEN_ENDPOINT = (
    "https://identity.insula.earth/realms/phisat2/protocol/openid-connect/token"
)
DEFAULT_REDIRECT_URI = "http://localhost:9207/auth"
DEFAULT_CLIENT_ID = "api-client"
DEFAULT_RESULTS_PER_PAGE = 50
DEFAULT_CATALOGUE = "REF_DATA"
PHISAT2_L1_REF_DATA_COLLECTION = "phisat24e55ba83dd304ea9b018b65e9b17a7de"
_CONTENT_DISPOSITION_FILENAME_RE = re.compile(r'filename="?([^";]+)"?')


def _compute_backoff_delay(attempt_index: int, backoff_base: float, backoff_max: float) -> float:
    """Compute retry delay with exponential backoff and jitter."""
    exponential = backoff_base * (2 ** attempt_index)
    return min(backoff_max, exponential) + random.uniform(0.0, 0.5)


def _strip_quotes(value: str) -> str:
    return value.strip().strip("'\"")


def _load_config_parser(config_file: str) -> configparser.ConfigParser:
    parser = configparser.ConfigParser()
    if os.path.exists(config_file):
        parser.read(config_file)
    return parser


def _write_config_parser(config_file: str, parser: configparser.ConfigParser) -> None:
    config_path = Path(config_file)
    if config_path.parent != Path("."):
        config_path.parent.mkdir(parents=True, exist_ok=True)
    with config_path.open("w", encoding="utf-8") as handle:
        parser.write(handle)


@dataclass(frozen=True)
class PhiSat2Config:
    username: str
    password: str
    base_url: str = DEFAULT_BASE_URL
    api_base: str = DEFAULT_API_BASE
    authorization_endpoint: str = DEFAULT_AUTHORIZATION_ENDPOINT
    token_endpoint: str = DEFAULT_TOKEN_ENDPOINT
    redirect_uri: str = DEFAULT_REDIRECT_URI
    client_id: str = DEFAULT_CLIENT_ID


def ensure_phisat2_config(config_file: str, reset: bool = False) -> None:
    """Ensure the shared config file contains a PhiSat-2 credential section."""
    parser = _load_config_parser(config_file)
    has_existing = (
        parser.has_section(PHISAT2_SECTION)
        and _strip_quotes(parser.get(PHISAT2_SECTION, "username", fallback=""))
        and _strip_quotes(parser.get(PHISAT2_SECTION, "password", fallback=""))
    )
    if has_existing and not reset:
        return

    if not parser.has_section(PHISAT2_SECTION):
        parser.add_section(PHISAT2_SECTION)

    username = input("Enter PhiSat-2 username/email: ").strip()
    password = getpass.getpass("Enter PhiSat-2 password: ").strip()

    parser.set(PHISAT2_SECTION, "username", username)
    parser.set(PHISAT2_SECTION, "password", password)
    parser.set(PHISAT2_SECTION, "base_url", DEFAULT_BASE_URL)
    parser.set(PHISAT2_SECTION, "api_base", DEFAULT_API_BASE)
    parser.set(PHISAT2_SECTION, "authorization_endpoint", DEFAULT_AUTHORIZATION_ENDPOINT)
    parser.set(PHISAT2_SECTION, "token_endpoint", DEFAULT_TOKEN_ENDPOINT)
    parser.set(PHISAT2_SECTION, "redirect_uri", DEFAULT_REDIRECT_URI)
    parser.set(PHISAT2_SECTION, "client_id", DEFAULT_CLIENT_ID)
    _write_config_parser(config_file, parser)
    logger.info("Updated %s with a [%s] credential section.", config_file, PHISAT2_SECTION)


def _read_phisat2_config(config_file: str) -> PhiSat2Config:
    parser = _load_config_parser(config_file)
    if not parser.has_section(PHISAT2_SECTION):
        raise ValueError(
            f"Configuration file {config_file} is missing a [{PHISAT2_SECTION}] section"
        )

    section = parser[PHISAT2_SECTION]
    username = _strip_quotes(section.get("username", ""))
    password = _strip_quotes(section.get("password", ""))
    if not username or not password:
        raise ValueError(
            f"Configuration file {config_file} must define {PHISAT2_SECTION}.username "
            f"and {PHISAT2_SECTION}.password"
        )

    base_url = _strip_quotes(section.get("base_url", DEFAULT_BASE_URL)) or DEFAULT_BASE_URL
    api_base = _strip_quotes(section.get("api_base", DEFAULT_API_BASE)) or DEFAULT_API_BASE
    authorization_endpoint = (
        _strip_quotes(section.get("authorization_endpoint", DEFAULT_AUTHORIZATION_ENDPOINT))
        or DEFAULT_AUTHORIZATION_ENDPOINT
    )
    token_endpoint = (
        _strip_quotes(section.get("token_endpoint", DEFAULT_TOKEN_ENDPOINT))
        or DEFAULT_TOKEN_ENDPOINT
    )
    redirect_uri = _strip_quotes(section.get("redirect_uri", DEFAULT_REDIRECT_URI)) or DEFAULT_REDIRECT_URI
    client_id = _strip_quotes(section.get("client_id", DEFAULT_CLIENT_ID)) or DEFAULT_CLIENT_ID

    return PhiSat2Config(
        username=username,
        password=password,
        base_url=base_url,
        api_base=api_base,
        authorization_endpoint=authorization_endpoint,
        token_endpoint=token_endpoint,
        redirect_uri=redirect_uri,
        client_id=client_id,
    )


def _get_auth_header(config: PhiSat2Config) -> str:
    try:
        from InsulaWorkflowClient import InsulaOpenIDConnect
    except ImportError as exc:
        raise ImportError(
            "PhiSat-2 support requires the InsulaWorkflowClient package. "
            "Install phidown from the updated package metadata or add "
            "'InsulaWorkflowClient' to your environment."
        ) from exc

    auth_client = InsulaOpenIDConnect(
        authorization_endpoint=config.authorization_endpoint,
        token_endpoint=config.token_endpoint,
        redirect_uri=config.redirect_uri,
        client_id=config.client_id,
    )
    auth_client.set_user_credentials(username=config.username, password=config.password)
    return auth_client.get_authorization_header()


def _build_headers(config: PhiSat2Config) -> typing.Dict[str, str]:
    return {
        "Authorization": _get_auth_header(config),
        "Content-Type": "application/json",
    }


def _normalize_platform_files(payload: typing.Dict[str, typing.Any], api_base: str) -> pd.DataFrame:
    records = payload.get("_embedded", {}).get("platformFiles", [])
    df = pd.DataFrame.from_records(records)
    if df.empty:
        return df

    if "id" in df.columns and "Id" not in df.columns:
        df["Id"] = df["id"]
    if "filename" in df.columns and "Name" not in df.columns:
        df["Name"] = df["filename"]
    if "contentLength" in df.columns and "ContentLength" not in df.columns:
        df["ContentLength"] = df["contentLength"]
    if "createdAt" in df.columns and "CreatedAt" not in df.columns:
        df["CreatedAt"] = df["createdAt"]
    if "id" in df.columns and "DownloadUrl" not in df.columns:
        df["DownloadUrl"] = df["id"].map(lambda value: f"{api_base}/platformFiles/{value}/dl")
    df["Provider"] = "phisat2"
    return df


def _nested_href(value: typing.Any) -> typing.Optional[str]:
    if isinstance(value, dict):
        href = value.get("href")
        if isinstance(href, str):
            return href
    return None


def _name_or_basename_matches(series: pd.Series, product_name: str) -> pd.Series:
    names = series.astype(str)
    basenames = names.map(lambda value: os.path.basename(value.rstrip("/")))
    return (names == product_name) | (basenames == product_name)


def _normalize_catalogue_features(payload: typing.Dict[str, typing.Any]) -> pd.DataFrame:
    features = payload.get("features", [])
    records: typing.List[typing.Dict[str, typing.Any]] = []

    for feature in features:
        if not isinstance(feature, dict):
            continue
        properties = feature.get("properties", {})
        if not isinstance(properties, dict):
            properties = {}

        links = properties.get("_links", {})
        if not isinstance(links, dict):
            links = {}

        services = properties.get("services", {})
        if not isinstance(services, dict):
            services = {}
        download_service = services.get("download", {})
        if not isinstance(download_service, dict):
            download_service = {}

        name = (
            properties.get("filename")
            or properties.get("productIdentifier")
            or properties.get("title")
            or feature.get("id")
        )
        download_url = _nested_href(links.get("download")) or download_service.get("url")

        record = {
            "Id": feature.get("id"),
            "Name": name,
            "ContentLength": properties.get("filesize") or download_service.get("size"),
            "ContentDate": {
                "Start": properties.get("startDate"),
                "End": properties.get("completionDate"),
            },
            "GeoFootprint": feature.get("geometry"),
            "DownloadUrl": download_url,
            "Provider": "phisat2",
            "Collection": properties.get("collection"),
            "ProductType": properties.get("productType") or properties.get("processingLevel"),
            "OriginDate": properties.get("published") or properties.get("updated"),
            "PlatformUrl": properties.get("platformUrl"),
        }
        records.append(record)

    return pd.DataFrame.from_records(records)


def _resolve_download_name(
    response: requests.Response,
    *,
    fallback_name: typing.Optional[str],
    product_id: typing.Union[str, int],
) -> str:
    disposition = response.headers.get("content-disposition", "")
    match = _CONTENT_DISPOSITION_FILENAME_RE.search(disposition)
    if match:
        return match.group(1).strip()
    if fallback_name:
        return os.path.basename(str(fallback_name).rstrip("/"))
    return f"{product_id}.zip"


def _download_stream_to_path(
    response: requests.Response,
    target_path: str,
    *,
    show_progress: bool,
) -> None:
    temp_path = f"{target_path}.part"
    total_size = int(response.headers.get("content-length", 0))

    if os.path.exists(temp_path):
        os.remove(temp_path)

    progress: typing.Optional[tqdm] = None
    if show_progress and total_size > 0:
        progress = tqdm(
            total=total_size,
            unit="B",
            unit_scale=True,
            unit_divisor=1024,
            desc=f"Downloading {os.path.basename(target_path)}",
        )

    try:
        with open(temp_path, "wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if not chunk:
                    continue
                handle.write(chunk)
                if progress is not None:
                    progress.update(len(chunk))
        os.replace(temp_path, target_path)
    finally:
        if progress is not None:
            progress.close()


class PhiSat2Searcher:
    """Search and download PhiSat-2 products from INSULA."""

    def __init__(self, config_file: str = ".s5cfg") -> None:
        self.config_file = config_file
        self.response: typing.Optional[requests.Response] = None
        self.json_data: typing.Optional[typing.Dict[str, typing.Any]] = None
        self.df: typing.Optional[pd.DataFrame] = None
        self.last_filter: typing.Optional[str] = None
        self.last_results_per_page: typing.Optional[int] = None

    def query(
        self,
        filter_text: str,
        *,
        results_per_page: int = DEFAULT_RESULTS_PER_PAGE,
        reset_config: bool = False,
    ) -> pd.DataFrame:
        """Search PhiSat-2 platform files by free-text filter."""
        if not isinstance(filter_text, str):
            raise TypeError("filter_text must be a string")
        if not filter_text.strip():
            raise ValueError("filter_text cannot be empty")
        if not isinstance(results_per_page, int) or results_per_page <= 0:
            raise ValueError("results_per_page must be a positive integer")

        ensure_phisat2_config(self.config_file, reset=reset_config)
        config = _read_phisat2_config(self.config_file)
        self.last_filter = filter_text.strip()
        self.last_results_per_page = results_per_page

        search_url = f"{config.api_base}/platformFiles/search/parametricFind"
        self.response = requests.get(
            search_url,
            params={"filter": self.last_filter, "resultsPerPage": results_per_page},
            headers=_build_headers(config),
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        self.response.raise_for_status()

        self.json_data = self.response.json()
        self.df = _normalize_platform_files(self.json_data, config.api_base)
        return self.df

    def query_catalogue(
        self,
        product_type: str = "L1",
        *,
        aoi_wkt: typing.Optional[str] = None,
        start_date: typing.Optional[str] = None,
        end_date: typing.Optional[str] = None,
        results_per_page: int = DEFAULT_RESULTS_PER_PAGE,
        page: int = 0,
        ref_data_collection: str = PHISAT2_L1_REF_DATA_COLLECTION,
        reset_config: bool = False,
    ) -> pd.DataFrame:
        """Search PhiSat-2 catalogue products with date and AOI filters."""
        if not isinstance(product_type, str) or not product_type.strip():
            raise ValueError("product_type must be a non-empty string")
        if not isinstance(results_per_page, int) or results_per_page <= 0:
            raise ValueError("results_per_page must be a positive integer")
        if not isinstance(page, int) or page < 0:
            raise ValueError("page must be a non-negative integer")

        ensure_phisat2_config(self.config_file, reset=reset_config)
        config = _read_phisat2_config(self.config_file)

        params: typing.Dict[str, typing.Any] = {
            "catalogue": DEFAULT_CATALOGUE,
            "refDataCollection": ref_data_collection,
            "identifier": product_type.strip(),
            "resultsPerPage": results_per_page,
            "page": page,
        }
        if aoi_wkt:
            params["aoi"] = aoi_wkt
        if start_date:
            params["productDateStart"] = start_date
        if end_date:
            params["productDateEnd"] = end_date

        self.last_filter = product_type.strip()
        self.last_results_per_page = results_per_page
        self.response = requests.get(
            f"{config.api_base}/search",
            params=params,
            headers=_build_headers(config),
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        self.response.raise_for_status()

        self.json_data = self.response.json()
        self.df = _normalize_catalogue_features(self.json_data)
        return self.df

    def query_by_name(
        self,
        product_name: str,
        *,
        results_per_page: int = DEFAULT_RESULTS_PER_PAGE,
        reset_config: bool = False,
    ) -> pd.DataFrame:
        """Search by filename and prefer exact filename matches."""
        results = self.query(
            product_name,
            results_per_page=results_per_page,
            reset_config=reset_config,
        )
        if results.empty:
            return results
        if "Name" not in results.columns:
            return results
        exact_matches = results[_name_or_basename_matches(results["Name"], product_name)].copy()
        if not exact_matches.empty:
            return exact_matches.reset_index(drop=True)
        if len(results) == 1:
            return results.reset_index(drop=True)
        return results.iloc[0:0].copy()

    def resolve_product(
        self,
        product_name: str,
        *,
        results_per_page: int = DEFAULT_RESULTS_PER_PAGE,
        reset_config: bool = False,
    ) -> pd.Series:
        """Resolve a product name or unique search token to one platform file."""
        if not isinstance(product_name, str) or not product_name.strip():
            raise ValueError("product_name cannot be empty")

        results = self.query(
            product_name,
            results_per_page=results_per_page,
            reset_config=reset_config,
        )
        if results.empty:
            raise FileNotFoundError(f"PhiSat-2 product not found: {product_name}")

        if "Name" in results.columns:
            exact_matches = results[_name_or_basename_matches(results["Name"], product_name)]
            if len(exact_matches) == 1:
                return exact_matches.iloc[0]
            if len(exact_matches) > 1:
                raise ValueError(
                    f"Multiple PhiSat-2 products matched the exact filename {product_name}. "
                    "Refine the filter or inspect matches with `phidown --list --provider phisat2`."
                )

        if len(results) == 1:
            return results.iloc[0]

        raise ValueError(
            f"Multiple PhiSat-2 products matched {product_name}. "
            "Refine the filter or inspect matches with `phidown --list --provider phisat2`."
        )

    def download_product(
        self,
        product_id: typing.Union[str, int],
        output_dir: str,
        *,
        file_name: typing.Optional[str] = None,
        reset_config: bool = False,
        show_progress: bool = True,
        retry_count: int = 1,
        connect_timeout: float = DEFAULT_CONNECT_TIMEOUT_SECONDS,
        read_timeout: float = DEFAULT_READ_TIMEOUT_SECONDS,
        backoff_base: float = 2.0,
        backoff_max: float = 60.0,
        overwrite: bool = False,
        unzip: bool = False,
    ) -> str:
        """Download one PhiSat-2 platform file by ID."""
        abs_output_dir = os.path.abspath(output_dir)
        os.makedirs(abs_output_dir, exist_ok=True)

        attempts = max(1, int(retry_count))
        should_reset_config = reset_config
        last_error: typing.Optional[Exception] = None

        for attempt in range(attempts):
            try:
                ensure_phisat2_config(self.config_file, reset=should_reset_config)
                should_reset_config = False
                config = _read_phisat2_config(self.config_file)
                download_url = f"{config.api_base}/platformFiles/{product_id}/dl"
                response = requests.get(
                    download_url,
                    headers=_build_headers(config),
                    stream=True,
                    timeout=(float(connect_timeout), float(read_timeout)),
                )
                response.raise_for_status()
                target_name = _resolve_download_name(
                    response,
                    fallback_name=file_name,
                    product_id=product_id,
                )
                target_path = os.path.join(abs_output_dir, target_name)
                if os.path.exists(target_path) and not overwrite and os.path.getsize(target_path) > 0:
                    logger.info("PhiSat-2 target already exists, skipping: %s", target_path)
                    return target_path
                _download_stream_to_path(response, target_path, show_progress=show_progress)
                if unzip and zipfile.is_zipfile(target_path):
                    extract_dir = os.path.join(abs_output_dir, Path(target_name).stem)
                    os.makedirs(extract_dir, exist_ok=True)
                    with zipfile.ZipFile(target_path, "r") as archive:
                        archive.extractall(extract_dir)
                    return extract_dir
                return target_path
            except Exception as exc:  # pragma: no cover - retried path covered by tests
                last_error = exc
                if attempt < attempts - 1:
                    delay = _compute_backoff_delay(attempt, backoff_base=backoff_base, backoff_max=backoff_max)
                    logger.warning(
                        "PhiSat-2 download attempt %s/%s failed (%s). Retrying in %.1fs...",
                        attempt + 1,
                        attempts,
                        exc,
                        delay,
                    )
                    time.sleep(delay)

        if last_error is None:
            raise RuntimeError("PhiSat-2 download failed without an explicit exception")
        raise last_error

    def download_url(
        self,
        download_url: str,
        output_dir: str,
        *,
        file_name: typing.Optional[str] = None,
        reset_config: bool = False,
        show_progress: bool = True,
        retry_count: int = 1,
        connect_timeout: float = DEFAULT_CONNECT_TIMEOUT_SECONDS,
        read_timeout: float = DEFAULT_READ_TIMEOUT_SECONDS,
        backoff_base: float = 2.0,
        backoff_max: float = 60.0,
        overwrite: bool = False,
        unzip: bool = False,
    ) -> str:
        """Download one PhiSat-2 product from a normalized download URL."""
        if not isinstance(download_url, str) or not download_url.strip():
            raise ValueError("download_url cannot be empty")

        abs_output_dir = os.path.abspath(output_dir)
        os.makedirs(abs_output_dir, exist_ok=True)

        attempts = max(1, int(retry_count))
        should_reset_config = reset_config
        last_error: typing.Optional[Exception] = None

        for attempt in range(attempts):
            try:
                ensure_phisat2_config(self.config_file, reset=should_reset_config)
                should_reset_config = False
                config = _read_phisat2_config(self.config_file)
                response = requests.get(
                    download_url,
                    headers=_build_headers(config),
                    stream=True,
                    timeout=(float(connect_timeout), float(read_timeout)),
                )
                response.raise_for_status()
                target_name = _resolve_download_name(
                    response,
                    fallback_name=file_name,
                    product_id=os.path.basename(download_url.rstrip("/")),
                )
                target_path = os.path.join(abs_output_dir, target_name)
                if os.path.exists(target_path) and not overwrite and os.path.getsize(target_path) > 0:
                    logger.info("PhiSat-2 target already exists, skipping: %s", target_path)
                    return target_path
                _download_stream_to_path(response, target_path, show_progress=show_progress)
                if unzip and zipfile.is_zipfile(target_path):
                    extract_dir = os.path.join(abs_output_dir, Path(target_name).stem)
                    os.makedirs(extract_dir, exist_ok=True)
                    with zipfile.ZipFile(target_path, "r") as archive:
                        archive.extractall(extract_dir)
                    return extract_dir
                return target_path
            except Exception as exc:  # pragma: no cover - retried path covered by tests
                last_error = exc
                if attempt < attempts - 1:
                    delay = _compute_backoff_delay(attempt, backoff_base=backoff_base, backoff_max=backoff_max)
                    logger.warning(
                        "PhiSat-2 download attempt %s/%s failed (%s). Retrying in %.1fs...",
                        attempt + 1,
                        attempts,
                        exc,
                        delay,
                    )
                    time.sleep(delay)

        if last_error is None:
            raise RuntimeError("PhiSat-2 download failed without an explicit exception")
        raise last_error

    def download_by_name(
        self,
        product_name: str,
        output_dir: str,
        *,
        results_per_page: int = DEFAULT_RESULTS_PER_PAGE,
        reset_config: bool = False,
        show_progress: bool = True,
        retry_count: int = 1,
        connect_timeout: float = DEFAULT_CONNECT_TIMEOUT_SECONDS,
        read_timeout: float = DEFAULT_READ_TIMEOUT_SECONDS,
        backoff_base: float = 2.0,
        backoff_max: float = 60.0,
        overwrite: bool = False,
        unzip: bool = False,
    ) -> str:
        """Resolve and download one PhiSat-2 platform file by filename or unique token."""
        resolved = self.resolve_product(
            product_name,
            results_per_page=results_per_page,
            reset_config=reset_config,
        )
        return self.download_product(
            product_id=resolved["Id"],
            output_dir=output_dir,
            file_name=resolved.get("Name"),
            reset_config=False,
            show_progress=show_progress,
            retry_count=retry_count,
            connect_timeout=connect_timeout,
            read_timeout=read_timeout,
            backoff_base=backoff_base,
            backoff_max=backoff_max,
            overwrite=overwrite,
            unzip=unzip,
        )
