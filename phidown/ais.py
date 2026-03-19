"""AIS (Automatic Identification System) data downloader and filtering utilities.

This module provides functionality to download, filter, and process AIS data from
Hugging Face datasets based on date ranges, time windows, and Areas of Interest (AOI).
"""

from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import List, Optional, Tuple, Union
import warnings

import pandas as pd
from huggingface_hub import hf_hub_download

try:
    from shapely import wkt as shapely_wkt
    from shapely.geometry import Point
    SHAPELY_AVAILABLE = True
except ImportError:
    shapely_wkt = None
    Point = None
    SHAPELY_AVAILABLE = False


class AISDataHandler:
    """Handler for downloading and filtering AIS data from Hugging Face datasets.
    
    This class provides methods to download AIS data for specified date ranges,
    filter by time windows, and apply spatial filtering using Areas of Interest (AOI).
    
    Attributes:
        hf_repo_id (str): Hugging Face repository ID for AIS data.
        file_template (str): Template for AIS data filenames.
        date_format (str): Date format string.
        verbose (bool): Whether to print progress messages.
    """
    
    def __init__(
        self, 
        hf_repo_id: str = "Lore0123/AISPortal",
        file_template: str = "{date}_ais.parquet",
        date_format: str = "%Y-%m-%d",
        verbose: bool = True
    ) -> None:
        """Initialize the AIS data handler.
        
        Args:
            hf_repo_id: Hugging Face repository ID containing AIS data.
            file_template: Template for AIS data filenames with {date} placeholder.
            date_format: Date format string for parsing dates.
            verbose: Whether to print progress and error messages.
        """
        self.hf_repo_id = hf_repo_id
        self.file_template = file_template
        self.date_format = date_format
        self.verbose = verbose
        self._errors: List[str] = []
    
    def get_ais_data(
        self,
        start_date: Union[str, date],
        end_date: Optional[Union[str, date]] = None,
        start_time: Optional[Union[str, time]] = None,
        end_time: Optional[Union[str, time]] = None,
        aoi_wkt: Optional[str] = None,
        verbose: Optional[bool] = None
    ) -> pd.DataFrame:
        """Download and filter AIS data based on date range, time window, and AOI.
        
        Args:
            start_date: Start date for data retrieval (YYYY-MM-DD string or date object).
            end_date: End date for data retrieval. If None, uses start_date.
            start_time: Start time for daily filtering (HH:MM:SS string or time object).
            end_time: End time for daily filtering (HH:MM:SS string or time object).
            aoi_wkt: Area of Interest as WKT polygon string for spatial filtering.
            verbose: Whether to print progress messages. If None, uses instance default.
            
        Returns:
            Filtered pandas DataFrame containing AIS data with standardized columns:
            - name: Vessel name
            - lat: Latitude
            - lon: Longitude
            - source_date: Date of data source
            - timestamp: Timestamp in YYYY-MM-DD HH:MM:SS format
            - mmsi: Maritime Mobile Service Identity
            - Plus all additional columns from the original AIS dataset
            (COG, SOG, HEADING, NAVSTAT, IMO, CALLSIGN, TYPE, etc.)
            
        Raises:
            ValueError: If date parsing fails or no valid data is found.
        """
        # Use method parameter or fall back to instance default
        use_verbose = verbose if verbose is not None else self.verbose
        
        self._errors.clear()
        
        # Parse and validate dates
        start_date_obj = self._parse_date(start_date)
        if start_date_obj is None:
            raise ValueError(f"Invalid start_date: {start_date}")
        
        end_date_obj = self._parse_date(end_date) if end_date else start_date_obj
        if end_date_obj is None:
            raise ValueError(f"Invalid end_date: {end_date}")
        
        # Parse time objects
        start_time_obj = self._parse_time(start_time) if start_time else None
        end_time_obj = self._parse_time(end_time) if end_time else None
        
        # Get date range
        dates = self._iterate_dates(start_date_obj, end_date_obj)
        if not dates:
            raise ValueError("No valid dates in range")
        
        # Load and process data
        df = self._load_ais_points(dates, start_time_obj, end_time_obj, use_verbose)
        
        # Apply spatial filtering if AOI provided
        if aoi_wkt:
            df = self._filter_by_aoi(df, aoi_wkt, use_verbose)
        
        # Print any errors that occurred
        if self._errors and use_verbose:
            print(f'Errors encountered during processing:')
            for error in self._errors:
                print(f'  - {error}')
        
        return df
    
    def get_errors(self) -> List[str]:
        """Get list of errors encountered during data processing.
        
        Returns:
            List of error messages from the last data retrieval operation.
        """
        return self._errors.copy()
    
    def _parse_date(self, value: Union[str, date, None]) -> Optional[date]:
        """Parse various date formats into date object.
        
        Args:
            value: Date as string, date object, or None.
            
        Returns:
            Parsed date object or None if parsing fails.
        """
        if not value:
            return None
        if isinstance(value, date):
            return value
        if isinstance(value, str):
            raw = value.strip()
            if not raw:
                return None
            try:
                return datetime.strptime(raw, self.date_format).date()
            except ValueError:
                return None
        return None
    
    def _parse_time(self, value: Union[str, time, None]) -> Optional[time]:
        """Parse time string into time object.
        
        Args:
            value: Time as string, time object, or None.
            
        Returns:
            Parsed time object or None if parsing fails.
        """
        if not value:
            return None
        if isinstance(value, time):
            return value
        if isinstance(value, str):
            raw = value.strip()
            if not raw:
                return None
            
            # Remove timezone suffixes (Z, +00:00, etc.)
            if raw.endswith('Z'):
                raw = raw[:-1]
            elif '+' in raw:
                raw = raw.split('+')[0]
            elif raw.endswith('UTC'):
                raw = raw[:-3]
            
            # Try different time formats including microseconds
            time_formats = [
                "%H:%M:%S.%f",  # HH:MM:SS.microseconds
                "%H:%M:%S",     # HH:MM:SS
                "%H:%M",        # HH:MM
            ]
            
            for fmt in time_formats:
                try:
                    parsed = datetime.strptime(raw, fmt)
                    return parsed.time()
                except ValueError:
                    continue
        return None
    
    def _iterate_dates(self, start: date, end: date) -> List[date]:
        """Generate list of dates between start and end (inclusive).
        
        Args:
            start: Start date.
            end: End date.
            
        Returns:
            List of date objects in the range.
        """
        if end < start:
            start, end = end, start
        
        current = start
        dates: List[date] = []
        while current <= end:
            dates.append(current)
            current += timedelta(days=1)
        return dates
    
    def _normalize_column_key(self, value: str) -> str:
        """Normalize column name for flexible matching.
        
        Args:
            value: Column name to normalize.
            
        Returns:
            Normalized column name (lowercase, alphanumeric only).
        """
        return "".join(ch for ch in value.lower() if ch.isalnum())
    
    def _find_column(self, df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
        """Find column in DataFrame using flexible name matching.
        
        Args:
            df: DataFrame to search.
            candidates: List of possible column names.
            
        Returns:
            Actual column name if found, None otherwise.
        """
        normalized_map = {}
        for col in df.columns:
            normalized_map.setdefault(self._normalize_column_key(col), col)
        
        for candidate in candidates:
            key = self._normalize_column_key(candidate)
            if key in normalized_map:
                return normalized_map[key]
        
        return None
    
    def _build_time_mask(
        self,
        datetimes: pd.Series,
        start_time_obj: Optional[time],
        end_time_obj: Optional[time]
    ) -> Optional[pd.Series]:
        """Build boolean mask for time filtering.
        
        Args:
            datetimes: Series of datetime values.
            start_time_obj: Start time for filtering.
            end_time_obj: End time for filtering.
            
        Returns:
            Boolean mask Series or None if no time filtering needed.
        """
        if start_time_obj is None and end_time_obj is None:
            return None
        
        dt_series = pd.to_datetime(datetimes, errors="coerce", utc=False)
        valid = dt_series.notna()
        times = dt_series.dt.time
        cond = pd.Series(True, index=dt_series.index)
        
        if start_time_obj and end_time_obj:
            if start_time_obj <= end_time_obj:
                # Normal case: 10:00 to 14:00
                cond &= (times >= start_time_obj) & (times <= end_time_obj)
            else:
                # Overnight case: 22:00 to 06:00
                cond &= (times >= start_time_obj) | (times <= end_time_obj)
        elif start_time_obj:
            cond &= times >= start_time_obj
        elif end_time_obj:
            cond &= times <= end_time_obj
        
        return cond & valid
    
    def _load_ais_points(
        self,
        dates: List[date],
        start_time_obj: Optional[time],
        end_time_obj: Optional[time],
        verbose: bool = True
    ) -> pd.DataFrame:
        """Load AIS data for multiple dates and apply time filtering.
        
        Args:
            dates: List of dates to load data for.
            start_time_obj: Start time for daily filtering.
            end_time_obj: End time for daily filtering.
            verbose: Whether to print progress messages.
            
        Returns:
            Concatenated and filtered DataFrame.
        """
        frames: List[pd.DataFrame] = []
        
        for day in dates:
            filename = self.file_template.format(date=day.isoformat())
            
            try:
                local_path = hf_hub_download(
                    repo_id=self.hf_repo_id,
                    filename=filename,
                    repo_type="dataset"
                )
            except Exception as exc:
                self._errors.append(f'{day}: download failed ({exc})')
                if verbose:
                    print(f'Download failed for {filename}: {exc}')
                continue
            
            try:
                df = pd.read_parquet(local_path)
            except Exception as exc:
                self._errors.append(f'{day}: failed to read parquet ({exc})')
                if verbose:
                    print(f'Failed to read parquet {filename}: {exc}')
                continue
            
            # Find coordinate columns
            lat_col = self._find_column(df, ["lat", "latitude"])
            lon_col = self._find_column(df, ["lon", "longitude", "long", "lng"])
            if lat_col is None or lon_col is None:
                self._errors.append(f'{day}: missing latitude/longitude columns')
                if verbose:
                    print(f'Missing coordinate columns for {filename}. Available columns: {list(df.columns)}')
                continue
            
            # Apply time filtering if requested
            time_col = self._find_column(df, [
                "tstamp", "timestamp", "time", "datetime", "basedatetime",
                "baseDateTime", "received_time", "receivedtime"
            ])
            
            if time_col is not None:
                mask = self._build_time_mask(df[time_col], start_time_obj, end_time_obj)
                if mask is not None:
                    df = df[mask.fillna(False)]
            elif start_time_obj or end_time_obj:
                self._errors.append(f'{day}: no timestamp column for time filtering')
            
            if df.empty:
                if verbose:
                    print(f'No data remaining after time filtering for {filename}')
                continue
            
            # Validate and clean coordinates
            lat_series = pd.to_numeric(df[lat_col], errors="coerce")
            lon_series = pd.to_numeric(df[lon_col], errors="coerce")
            valid_mask = lat_series.notna() & lon_series.notna()
            
            if not valid_mask.any():
                if verbose:
                    print(f'No valid coordinates found for {filename}')
                continue
            
            subset = df.loc[valid_mask].copy()
            subset["lat"] = lat_series.loc[valid_mask].astype(float)
            subset["lon"] = lon_series.loc[valid_mask].astype(float)
            
            # Extract vessel name
            name_col = self._find_column(df, [
                "name", "shipname", "vessel", "imo", "callsign", "vesselname"
            ])
            if name_col is not None:
                subset_names = subset[name_col].fillna("").astype(str)
            else:
                subset_names = pd.Series("", index=subset.index)
            subset["name"] = subset_names.replace({"nan": "", "None": ""})
            
            # Add source date
            subset["source_date"] = day.isoformat()
            
            # Extract MMSI
            mmsi_col = self._find_column(df, ["mmsi", "mmsi_id"])
            if mmsi_col is not None:
                subset_mmsi = subset[mmsi_col].fillna("").astype(str)
                subset_mmsi = subset_mmsi.replace({"nan": "", "None": ""})
                subset["mmsi"] = subset_mmsi
            else:
                subset["mmsi"] = ""
            
            # Format timestamp
            if time_col is not None:
                ts_series = pd.to_datetime(subset[time_col], errors="coerce", utc=True)
                try:
                    ts_local = ts_series.dt.tz_convert(None)
                except TypeError:  # already naive
                    ts_local = ts_series
                subset["timestamp"] = ts_local.dt.strftime("%Y-%m-%d %H:%M:%S").fillna("")
            else:
                subset["timestamp"] = ""
            
            frames.append(subset.reset_index(drop=True))
            if verbose:
                print(f'Added {len(subset)} rows from {filename}')
        
        if not frames:
            if verbose:
                print('No valid data frames collected')
            return pd.DataFrame(columns=[
                "name", "lat", "lon", "source_date", "timestamp", "mmsi"
            ])
        
        result = pd.concat(frames, ignore_index=True)
        
        # Ensure standardized columns are first, then add all remaining columns
        standard_cols = ["name", "lat", "lon", "source_date", "timestamp", "mmsi"]
        remaining_cols = [col for col in result.columns if col not in standard_cols]
        
        # Reorder columns with standard ones first
        final_columns = standard_cols + remaining_cols
        final_result = result[final_columns]
        
        if verbose:
            print(f'Final result: {len(final_result)} rows total with {len(final_columns)} columns')
        return final_result
    
    def _filter_by_aoi(self, df: pd.DataFrame, wkt_text: str, verbose: bool = True) -> pd.DataFrame:
        """Filter DataFrame points by Area of Interest polygon.
        
        Args:
            df: DataFrame with lat/lon columns.
            wkt_text: WKT polygon string defining the AOI.
            verbose: Whether to print progress messages.
            
        Returns:
            Filtered DataFrame containing only points within the AOI.
            
        Raises:
            ValueError: If shapely is not available or WKT parsing fails.
        """
        wkt_clean = wkt_text.strip() if wkt_text else ""
        if not wkt_clean:
            return df
        
        if not SHAPELY_AVAILABLE or shapely_wkt is None or Point is None:
            warnings.warn(
                "Shapely not available. AOI filtering will be disabled. "
                "Install shapely to enable spatial filtering: pip install shapely",
                UserWarning
            )
            raise ValueError(
                "AOI filtering unavailable: shapely not installed. "
                "Install with: pip install shapely"
            )
        
        try:
            geom = shapely_wkt.loads(wkt_clean)
        except Exception as exc:
            raise ValueError(f"AOI parse error: {exc}")
        
        if geom.is_empty:
            self._errors.append("AOI geometry is empty")
            return df
        
        def contains_point(row) -> bool:
            """Check if point is within the AOI geometry."""
            try:
                if Point is None:
                    return False
                pt = Point(float(row["lon"]), float(row["lat"]))
                return geom.contains(pt) or geom.touches(pt)
            except Exception:
                return False
        
        mask = df.apply(contains_point, axis=1)
        filtered_df = df[mask].reset_index(drop=True)
        
        if filtered_df.empty:
            self._errors.append("AOI filter removed all points")
        
        return filtered_df


def download_ais_data(
    start_date: Union[str, date],
    end_date: Optional[Union[str, date]] = None,
    start_time: Optional[Union[str, time]] = None,
    end_time: Optional[Union[str, time]] = None,
    aoi_wkt: Optional[str] = None,
    hf_repo_id: str = "Lore0123/AISPortal",
    verbose: bool = True
) -> pd.DataFrame:
    """Convenience function to download and filter AIS data.
    
    Args:
        start_date: Start date for data retrieval (YYYY-MM-DD string or date object).
        end_date: End date for data retrieval. If None, uses start_date.
        start_time: Start time for daily filtering (HH:MM:SS string or time object).
        end_time: End time for daily filtering (HH:MM:SS string or time object).
        aoi_wkt: Area of Interest as WKT polygon string for spatial filtering.
        hf_repo_id: Hugging Face repository ID containing AIS data.
        verbose: Whether to print progress and error messages.
        
    Returns:
        Filtered pandas DataFrame containing AIS data with all available columns.
        Standardized columns (name, lat, lon, source_date, timestamp, mmsi) 
        are placed first, followed by all original AIS dataset columns.
        
    Example:
        >>> # Download data for a single day
        >>> df = download_ais_data("2025-08-25")
        
        >>> # Download with time window (silent)
        >>> df = download_ais_data(
        ...     "2025-08-25", 
        ...     start_time="10:00:00", 
        ...     end_time="12:00:00",
        ...     verbose=False
        ... )
        
        >>> # Download with AOI filtering
        >>> aoi = "POLYGON((4.21 51.37,4.48 51.37,4.51 51.29,4.47 51.17,4.25 51.17,4.19 51.25,4.21 51.37))"
        >>> df = download_ais_data("2025-08-25", aoi_wkt=aoi)
    """
    handler = AISDataHandler(hf_repo_id=hf_repo_id, verbose=verbose)
    return handler.get_ais_data(start_date, end_date, start_time, end_time, aoi_wkt)
