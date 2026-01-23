#!/usr/bin/env python3
"""
InSAR Data Acquisition Script

This script automates the search and download of Sentinel-1 SLC and/or burst SLC
products for InSAR processing. It supports:

- Full SLC or burst mode downloads
- Automatic optimal orbit and burst detection
- External configuration file (YAML) for all parameters
- Platform filtering (S1A, S1B, S1C, S1D or combinations)
- Temporal statistics and distribution plots
- Robust download with retry logic and validation

Usage:
    python insar.py config.yaml
    python insar.py config.yaml --dry-run
    python insar.py config.yaml --find-optimal
    python insar.py config.yaml --download

Author: ESA PhiLab
"""

import argparse
import hashlib
import json
import logging
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import yaml
import warnings
# Suppress specific warnings
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from phidown.search import CopernicusDataSearcher
from phidown.downloader import get_token, download_burst_on_demand, pull_down

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


# =============================================================================
# Configuration Data Classes
# =============================================================================

@dataclass
class SearchConfig:
    """Configuration for Sentinel-1 search parameters."""
    
    # AOI and temporal parameters
    aoi_wkt: str
    start_date: str
    end_date: str
    
    # Acquisition mode: 'burst' or 'slc'
    mode: str = 'slc'
    
    # Polarization: VV, VH, HH, HV
    polarisation: str = 'VV'
    
    # Orbit parameters (optional - will be auto-detected if not specified)
    orbit_direction: Optional[str] = None  # 'ASCENDING' or 'DESCENDING'
    relative_orbit: Optional[int] = None   # Track number (1-175)
    
    # Platform filtering: list of 'A', 'B', 'C', 'D' or 'all'
    platforms: List[str] = field(default_factory=lambda: ['all'])
    
    # Burst-specific parameters
    swath_identifier: Optional[str] = None  # IW1, IW2, IW3
    burst_id: Optional[int] = None
    
    # Result limits
    max_results: int = 1000

    def __post_init__(self):
        """Validate configuration after initialization."""
        # Normalize mode
        self.mode = self.mode.lower()
        if self.mode not in ['burst', 'slc', 'full_slc']:
            raise ValueError(f"Invalid mode: {self.mode}. Must be 'burst' or 'slc'")
        if self.mode == 'full_slc':
            self.mode = 'slc'
        
        # Normalize polarisation
        self.polarisation = self.polarisation.upper()
        if self.polarisation not in ['VV', 'VH', 'HH', 'HV']:
            raise ValueError(f"Invalid polarisation: {self.polarisation}")
        
        # Normalize orbit direction
        if self.orbit_direction:
            self.orbit_direction = self.orbit_direction.upper()
            if self.orbit_direction not in ['ASCENDING', 'DESCENDING']:
                raise ValueError(f"Invalid orbit_direction: {self.orbit_direction}")
        
        # Validate platforms
        if isinstance(self.platforms, str):
            self.platforms = [self.platforms]
        
        valid_platforms = ['A', 'B', 'C', 'D', 'ALL']
        for p in self.platforms:
            if p.upper() not in valid_platforms:
                raise ValueError(f"Invalid platform: {p}. Must be one of {valid_platforms}")
        
        self.platforms = [p.upper() for p in self.platforms]


@dataclass
class DownloadConfig:
    """Configuration for download parameters."""
    
    output_dir: str = './data'
    username: Optional[str] = None
    password: Optional[str] = None
    retry_count: int = 3
    validate_downloads: bool = True
    resume_incomplete: bool = True
    config_file: str = '.s5cfg'  # s5cmd config for S3 downloads

    def __post_init__(self):
        """Ensure output directory is absolute path."""
        self.output_dir = os.path.abspath(self.output_dir)


@dataclass
class InSARConfig:
    """Complete InSAR workflow configuration."""
    
    search: SearchConfig
    download: DownloadConfig
    output_statistics: str = './statistics'
    save_results_csv: bool = True


# =============================================================================
# Configuration Loading
# =============================================================================

def load_config(config_path: str) -> InSARConfig:
    """
    Load and validate configuration from YAML file.
    
    Args:
        config_path: Path to the YAML configuration file.
        
    Returns:
        InSARConfig object with validated parameters.
        
    Raises:
        FileNotFoundError: If config file doesn't exist.
        ValueError: If config parameters are invalid.
    """
    path = Path(config_path)
    
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")
    
    logger.info(f"📁 Loading configuration from: {path}")
    
    with open(path, 'r') as f:
        raw_config = yaml.safe_load(f)
    
    # Parse search configuration
    search_raw = raw_config.get('search', {})
    search_config = SearchConfig(
        aoi_wkt=search_raw.get('aoi_wkt', ''),
        start_date=search_raw.get('start_date', ''),
        end_date=search_raw.get('end_date', ''),
        mode=search_raw.get('mode', 'slc'),
        polarisation=search_raw.get('polarisation', 'VV'),
        orbit_direction=search_raw.get('orbit_direction'),
        relative_orbit=search_raw.get('relative_orbit'),
        platforms=search_raw.get('platforms', ['all']),
        swath_identifier=search_raw.get('swath_identifier'),
        burst_id=search_raw.get('burst_id'),
        max_results=search_raw.get('max_results', 1000)
    )
    
    # Parse download configuration
    download_raw = raw_config.get('download', {})
    download_config = DownloadConfig(
        output_dir=download_raw.get('output_dir', './data'),
        username=download_raw.get('username') or os.environ.get('CDSE_USERNAME'),
        password=download_raw.get('password') or os.environ.get('CDSE_PASSWORD'),
        retry_count=download_raw.get('retry_count', 3),
        validate_downloads=download_raw.get('validate_downloads', True),
        resume_incomplete=download_raw.get('resume_incomplete', True),
        config_file=download_raw.get('config_file', '.s5cfg')
    )
    
    # Create full config
    config = InSARConfig(
        search=search_config,
        download=download_config,
        output_statistics=raw_config.get('output_statistics', './statistics'),
        save_results_csv=raw_config.get('save_results_csv', True)
    )
    
    logger.info(f"✅ Configuration loaded successfully")
    logger.info(f"   Mode: {config.search.mode}")
    logger.info(f"   AOI: {config.search.aoi_wkt[:50]}...")
    logger.info(f"   Date range: {config.search.start_date} to {config.search.end_date}")
    
    return config


def create_sample_config(output_path: str = 'insar_config.yaml') -> None:
    """
    Create a sample configuration file.
    
    Args:
        output_path: Path where to save the sample configuration.
    """
    sample_config = """# InSAR Data Acquisition Configuration
# =====================================

# Search parameters for Sentinel-1 data
search:
  # Area of Interest in WKT format (EPSG:4326)
  # Polygon must be closed (first and last coordinates must match)
  aoi_wkt: |
    POLYGON((
      12.4 41.8,
      12.6 41.8,
      12.6 42.0,
      12.4 42.0,
      12.4 41.8
    ))
  
  # Temporal range (ISO 8601 format)
  start_date: "2024-08-01T00:00:00"
  end_date: "2024-09-01T00:00:00"
  
  # Acquisition mode: 'slc' for full SLC products, 'burst' for individual bursts
  # Note: Burst mode data available from August 2, 2024 onwards
  mode: slc
  
  # Polarisation channel: VV, VH, HH, or HV
  polarisation: VV
  
  # Orbit direction: ASCENDING, DESCENDING, or null for auto-detection
  # If null, the script will find the optimal orbit based on:
  # - Maximum AOI coverage
  # - Regional preference (Descending for EU/America, Ascending for Asia/Australia)
  orbit_direction: null
  
  # Relative orbit number (track): 1-175, or null for auto-detection
  relative_orbit: null
  
  # Platform filter: list of 'A' (S1A), 'B' (S1B), 'C' (S1C), 'D' (S1D), or 'all'
  platforms:
    - all
  
  # Burst-specific parameters (only used when mode=burst)
  # Swath identifier: IW1, IW2, IW3 (null for auto-selection)
  # IW1 is preferred (lowest incidence angle), then IW2, then IW3
  swath_identifier: null
  
  # Specific burst ID to search for (optional)
  burst_id: null
  
  # Maximum number of results to retrieve
  max_results: 1000

# Download parameters
download:
  # Output directory for downloaded data
  output_dir: ./data
  
  # CDSE credentials (required for burst downloads)
  # Can also be set via environment variables CDSE_USERNAME and CDSE_PASSWORD
  username: null
  password: null
  
  # Number of retry attempts for failed downloads
  retry_count: 3
  
  # Validate downloaded files (check for manifest.safe, file integrity)
  validate_downloads: true
  
  # Resume incomplete downloads
  resume_incomplete: true
  
  # Path to s5cmd configuration file (for S3 downloads)
  config_file: .s5cfg

# Output paths for statistics and results
output_statistics: ./statistics
save_results_csv: true
"""
    
    with open(output_path, 'w') as f:
        f.write(sample_config)
    
    logger.info(f"📝 Sample configuration saved to: {output_path}")


# =============================================================================
# Optimal Orbit and Burst Detection
# =============================================================================

# Regional bounds for orbit direction preferences
EUROPE_AMERICA_LON_BOUNDS = (-180, 60)   # Descending preferred
ASIA_AUSTRALIA_LON_BOUNDS = (60, 180)    # Ascending preferred

# Subswath priority (lower index = higher priority, lower incidence angle)
SUBSWATH_PRIORITY = {'IW1': 0, 'IW2': 1, 'IW3': 2}


def get_aoi_centroid(aoi_wkt: str) -> Tuple[float, float]:
    """
    Calculate the centroid of the AOI.
    
    Args:
        aoi_wkt: WKT polygon string.
        
    Returns:
        Tuple[float, float]: (longitude, latitude) of the centroid.
    """
    # Parse WKT polygon
    wkt_upper = aoi_wkt.upper()
    if not wkt_upper.startswith('POLYGON'):
        raise ValueError("AOI must be a WKT POLYGON")
    
    # Extract coordinates
    coord_str = aoi_wkt.split('((')[1].split('))')[0]
    coords = []
    for pair in coord_str.split(','):
        parts = pair.strip().split()
        if len(parts) >= 2:
            lon, lat = float(parts[0]), float(parts[1])
            coords.append((lon, lat))
    
    if not coords:
        raise ValueError("Could not parse AOI coordinates")
    
    # Calculate centroid (exclude closing point)
    coords = coords[:-1] if coords[0] == coords[-1] else coords
    lon_avg = sum(c[0] for c in coords) / len(coords)
    lat_avg = sum(c[1] for c in coords) / len(coords)
    
    return lon_avg, lat_avg


def get_recommended_orbit_direction(aoi_wkt: str) -> str:
    """
    Determine recommended orbit direction based on AOI location.
    
    Rules:
    - For Europe/America (longitude -180 to 60): Descending preferred
    - For Asia/Australia (longitude 60 to 180): Ascending preferred
    
    Args:
        aoi_wkt: WKT polygon string.
        
    Returns:
        str: Recommended orbit direction ('ASCENDING' or 'DESCENDING').
    """
    lon, _ = get_aoi_centroid(aoi_wkt)
    
    if EUROPE_AMERICA_LON_BOUNDS[0] <= lon < EUROPE_AMERICA_LON_BOUNDS[1]:
        return 'DESCENDING'
    else:
        return 'ASCENDING'


def find_optimal_orbit(
    config: InSARConfig,
    searcher: CopernicusDataSearcher
) -> Dict[str, Any]:
    """
    Find the optimal orbit direction and relative orbit for maximum AOI coverage.
    
    Args:
        config: InSAR configuration.
        searcher: Initialized CopernicusDataSearcher instance.
        
    Returns:
        Dict containing orbit analysis and recommendations.
    """
    logger.info("🔍 Finding optimal orbit configuration...")
    
    aoi = config.search.aoi_wkt
    start = config.search.start_date
    end = config.search.end_date
    
    results = {
        'ascending': {'orbits': {}, 'best_orbit': None, 'max_coverage': 0},
        'descending': {'orbits': {}, 'best_orbit': None, 'max_coverage': 0},
        'recommended': None
    }
    
    for direction in ['ASCENDING', 'DESCENDING']:
        logger.info(f"   Analyzing {direction} orbits...")
        
        # Build platform filter
        platform_filter = None
        platforms_upper = [p.upper() for p in config.search.platforms]
        if 'ALL' not in platforms_upper:
            platform_filter = config.search.platforms[0] if len(config.search.platforms) == 1 else None
        
        # Search for products
        searcher.query_by_filter(
            collection_name='SENTINEL-1',
            product_type='SLC',
            orbit_direction=direction,
            aoi_wkt=aoi,
            start_date=start,
            end_date=end,
            attributes={'platformSerialIdentifier': platform_filter} if platform_filter else None,
            top=100,
            count=True
        )
        
        df = searcher.execute_query()
        
        if df is None or df.empty:
            logger.info(f"   No products found for {direction} direction")
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
        
        if 'relative_orbit' not in df.columns or df['relative_orbit'].isna().all():
            continue
        
        # Use coverage if available
        if 'coverage' not in df.columns:
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
            valid_stats = orbit_stats.dropna(subset=['avg_coverage', 'relative_orbit'])
            if not valid_stats.empty:
                best_idx = valid_stats['avg_coverage'].idxmax()
                best_orbit = int(valid_stats.loc[best_idx, 'relative_orbit'])
                max_coverage = float(valid_stats.loc[best_idx, 'avg_coverage'])
                
                results[direction_key]['best_orbit'] = best_orbit
                results[direction_key]['max_coverage'] = max_coverage
                
                logger.info(f"   Best {direction} orbit: #{best_orbit} ({max_coverage:.1f}% avg coverage)")
    
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
        recommended_direction = get_recommended_orbit_direction(aoi)
        direction_key = recommended_direction.lower()
        results['recommended'] = {
            'orbit_direction': recommended_direction,
            'relative_orbit': results[direction_key]['best_orbit'],
            'expected_coverage': results[direction_key]['max_coverage']
        }
    
    if results['recommended']:
        rec = results['recommended']
        logger.info(f"🎯 RECOMMENDED: {rec['orbit_direction']} orbit #{rec['relative_orbit']} "
                   f"({rec['expected_coverage']:.1f}% coverage)")
    
    return results


def find_optimal_bursts(
    config: InSARConfig,
    searcher: CopernicusDataSearcher,
    orbit_direction: str,
    relative_orbit: Optional[int] = None
) -> pd.DataFrame:
    """
    Find optimal bursts covering the AOI with subswath preferences.
    
    Preferences:
    - IW1 preferred over IW2, IW3 preferred last (lower incident angle)
    
    Args:
        config: InSAR configuration.
        searcher: Initialized CopernicusDataSearcher instance.
        orbit_direction: Orbit direction to use.
        relative_orbit: Relative orbit number (optional).
        
    Returns:
        pd.DataFrame: Optimized burst selection sorted by preference.
    """
    logger.info("🔍 Finding optimal bursts...")
    
    # Determine subswath preference order
    if config.search.swath_identifier:
        preferred_subswaths = [config.search.swath_identifier]
    else:
        # Default preference: IW1 > IW2 > IW3 (lower incidence angle preferred)
        preferred_subswaths = ['IW1', 'IW2', 'IW3']
    
    # Build platform filter
    platform_filter = None
    platforms_upper = [p.upper() for p in config.search.platforms]
    if 'ALL' not in platforms_upper:
        platform_filter = config.search.platforms[0] if len(config.search.platforms) == 1 else None
    
    # Search bursts (note: relative_orbit_number works for burst mode)
    searcher.query_by_filter(
        burst_mode=True,
        orbit_direction=orbit_direction,
        relative_orbit_number=relative_orbit,
        aoi_wkt=config.search.aoi_wkt,
        start_date=config.search.start_date,
        end_date=config.search.end_date,
        polarisation_channels=config.search.polarisation,
        platform_serial_identifier=platform_filter,
        burst_id=config.search.burst_id,
        top=config.search.max_results,
        count=True
    )
    
    df = searcher.execute_query()
    
    if df is None or df.empty:
        logger.warning("No bursts found for the specified parameters")
        return pd.DataFrame()
    
    logger.info(f"   Found {len(df)} bursts (Total available: {searcher.num_results})")
    
    # Add subswath priority
    swath_priority = {swath: idx for idx, swath in enumerate(preferred_subswaths)}
    default_priority = len(preferred_subswaths)
    
    if 'SwathIdentifier' in df.columns:
        df['subswath_priority'] = df['SwathIdentifier'].apply(
            lambda x: swath_priority.get(x, default_priority)
        )
    else:
        df['subswath_priority'] = default_priority
    
    # Filter by platform if multiple specified
    platforms_upper = [p.upper() for p in config.search.platforms]
    if 'ALL' not in platforms_upper and len(config.search.platforms) > 1:
        if 'PlatformSerialIdentifier' in df.columns:
            df = df[df['PlatformSerialIdentifier'].isin(config.search.platforms)]
    
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
        logger.info(f"   Swath distribution:")
        for swath, count in swath_counts.items():
            logger.info(f"     {swath}: {count}")
    
    return df


# =============================================================================
# Search Functions
# =============================================================================

def search_slc_products(
    config: InSARConfig,
    searcher: CopernicusDataSearcher,
    orbit_direction: str,
    relative_orbit: Optional[int] = None
) -> pd.DataFrame:
    """
    Search for Sentinel-1 SLC products.
    
    Args:
        config: InSAR configuration.
        searcher: Initialized CopernicusDataSearcher instance.
        orbit_direction: Orbit direction to use.
        relative_orbit: Relative orbit number (optional).
        
    Returns:
        pd.DataFrame: Search results.
    """
    logger.info("🔍 Searching for SLC products...")
    
    # Build attributes filter (minimal to avoid API issues)
    attributes = {}
    
    # Platform filter
    platforms_upper = [p.upper() for p in config.search.platforms]
    if 'ALL' not in platforms_upper:
        if len(config.search.platforms) == 1:
            attributes['platformSerialIdentifier'] = config.search.platforms[0].upper()
    
    # Note: relativeOrbitNumber filtering is done client-side due to API issues
    # Note: polarisationChannels not filtered - SLC products contain all pols
    
    logger.info(f"   Orbit: {orbit_direction}, Relative orbit: {relative_orbit}")
    if attributes:
        logger.info(f"   Server-side filters: {attributes}")
    
    searcher.query_by_filter(
        collection_name='SENTINEL-1',
        product_type='SLC',
        orbit_direction=orbit_direction,
        aoi_wkt=config.search.aoi_wkt,
        start_date=config.search.start_date,
        end_date=config.search.end_date,
        attributes=attributes if attributes else None,
        top=config.search.max_results,
        count=True
    )
    
    df = searcher.execute_query()
    
    if df is None or df.empty:
        logger.warning("No SLC products found for the specified parameters")
        return pd.DataFrame()
    
    logger.info(f"   Found {len(df)} SLC products (Total available: {searcher.num_results})")
    
    # Extract attributes for filtering
    if 'Attributes' in df.columns:
        def get_attribute(attrs, name):
            if isinstance(attrs, list):
                for attr in attrs:
                    if attr.get('Name') == name:
                        return attr.get('Value')
            return None
        
        df['relativeOrbitNumber'] = df['Attributes'].apply(lambda x: get_attribute(x, 'relativeOrbitNumber'))
        df['platformSerialIdentifier'] = df['Attributes'].apply(lambda x: get_attribute(x, 'platformSerialIdentifier'))
        
        # Debug: Show unique orbit values
        unique_orbits = df['relativeOrbitNumber'].unique()
        logger.info(f"   Available relative orbits: {sorted([str(o) for o in unique_orbits if o is not None])}")
    
    # Filter by relative orbit (client-side)
    if relative_orbit and 'relativeOrbitNumber' in df.columns:
        # Try both string and int comparison
        orbit_str = str(relative_orbit)
        mask = (df['relativeOrbitNumber'] == orbit_str) | (df['relativeOrbitNumber'] == relative_orbit)
        df = df[mask]
        logger.info(f"   After orbit filter (#{relative_orbit}): {len(df)} products")
    
    # Filter by multiple platforms if needed (client-side)
    platforms_upper = [p.upper() for p in config.search.platforms]
    if 'ALL' not in platforms_upper and len(config.search.platforms) > 1:
        if 'platformSerialIdentifier' in df.columns:
            df = df[df['platformSerialIdentifier'].isin(config.search.platforms)]
            logger.info(f"   After platform filter: {len(df)} products")
    
    return df


# =============================================================================
# Temporal Statistics and Plotting
# =============================================================================

def compute_temporal_statistics(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Compute temporal statistics for search results.
    
    Args:
        df: DataFrame with search results.
        
    Returns:
        Dict containing temporal statistics.
    """
    if df is None or df.empty:
        return {}
    
    # Extract acquisition dates
    dates = None
    if 'ContentDate' in df.columns:
        dates = pd.to_datetime(df['ContentDate'].apply(
            lambda x: x.get('Start') if isinstance(x, dict) else x
        ))
    elif 'OriginDate' in df.columns:
        dates = pd.to_datetime(df['OriginDate'])
    
    if dates is None or dates.empty:
        return {}
    
    dates = dates.dropna().sort_values()
    
    if len(dates) == 0:
        return {}
    
    # Calculate statistics
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
            'acquisitions_by_month': {
                str(k): int(v) for k, v in 
                dates.dt.to_period('M').value_counts().sort_index().items()
            },
            'acquisitions_by_year': {
                int(k): int(v) for k, v in 
                dates.dt.year.value_counts().sort_index().items()
            }
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
    df: pd.DataFrame,
    output_path: str,
    title: str = 'Sentinel-1 Temporal Distribution Analysis'
) -> Optional[str]:
    """
    Create and save a plot of temporal distribution of acquisitions.
    
    Args:
        df: DataFrame with search results.
        output_path: Path to save the plot.
        title: Plot title.
        
    Returns:
        str: Path to saved plot, or None if failed.
    """
    try:
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
    except ImportError:
        logger.warning("matplotlib not installed. Skipping temporal plot.")
        return None
    
    if df is None or df.empty:
        logger.warning("No data for temporal plot")
        return None
    
    # Extract dates
    dates = None
    if 'ContentDate' in df.columns:
        dates = pd.to_datetime(df['ContentDate'].apply(
            lambda x: x.get('Start') if isinstance(x, dict) else x
        ))
    elif 'OriginDate' in df.columns:
        dates = pd.to_datetime(df['OriginDate'])
    
    if dates is None or len(dates.dropna()) < 2:
        logger.warning("Need at least 2 acquisitions for temporal plot")
        return None
    
    dates = dates.dropna().sort_values().reset_index(drop=True)
    
    # Create figure with subplots
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(title, fontsize=14, fontweight='bold')
    
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
    monthly_counts = dates.dt.to_period('M').value_counts().sort_index()
    months = [str(p) for p in monthly_counts.index]
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
    
    # Ensure output directory exists
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    logger.info(f"📊 Temporal distribution plot saved to: {output_path}")
    
    plt.close()
    
    return output_path


# =============================================================================
# Download Functions
# =============================================================================

def download_bursts(
    df: pd.DataFrame,
    config: InSARConfig,
    searcher: CopernicusDataSearcher
) -> Dict[str, Any]:
    """
    Download burst products with retry logic and validation.
    
    Args:
        df: DataFrame with burst products to download.
        config: InSAR configuration.
        searcher: Initialized CopernicusDataSearcher instance.
        
    Returns:
        Dict containing download summary.
    """
    if df is None or df.empty:
        logger.warning("No burst products to download")
        return {'downloaded': 0, 'failed': 0, 'skipped': 0, 'details': []}
    
    username = config.download.username
    password = config.download.password
    
    if not username or not password:
        raise ValueError(
            "CDSE credentials required for burst downloads. "
            "Set username/password in config or via CDSE_USERNAME/CDSE_PASSWORD env vars."
        )
    
    # Ensure output directory exists
    output_path = Path(config.download.output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"📥 Starting burst download to: {output_path}")
    
    # Get access token
    logger.info("🔐 Authenticating with CDSE...")
    try:
        token = get_token(username, password)
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        raise
    
    summary = {
        'downloaded': 0,
        'failed': 0,
        'skipped': 0,
        'details': []
    }
    
    total = len(df)
    for idx, row in df.iterrows():
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
        
        # Check if already downloaded (resume logic)
        if config.download.resume_incomplete:
            existing_files = list(output_path.glob(f'*{burst_num}*.zip'))
            if existing_files:
                logger.info(f"   ⏭️  Skipping burst {idx + 1}/{total} (already exists)")
                summary['skipped'] += 1
                summary['details'].append({
                    'burst_id': burst_id,
                    'burst_num': burst_num,
                    'status': 'skipped',
                    'reason': 'already_exists'
                })
                continue
        
        logger.info(f"📥 Downloading burst {idx + 1}/{total} (BurstId: {burst_num})...")
        
        success = False
        last_error = None
        
        for attempt in range(config.download.retry_count):
            try:
                download_burst_on_demand(
                    burst_id=burst_id,
                    token=token,
                    output_dir=output_path
                )
                success = True
                break
            except Exception as e:
                last_error = str(e)
                if attempt < config.download.retry_count - 1:
                    logger.warning(f"   ⚠️  Attempt {attempt + 1} failed, retrying...")
                    # Refresh token on failure
                    try:
                        token = get_token(username, password)
                    except:
                        pass
        
        if success:
            summary['downloaded'] += 1
            summary['details'].append({
                'burst_id': burst_id,
                'burst_num': burst_num,
                'status': 'success'
            })
            logger.info(f"   ✅ Downloaded successfully")
        else:
            summary['failed'] += 1
            summary['details'].append({
                'burst_id': burst_id,
                'burst_num': burst_num,
                'status': 'failed',
                'error': last_error
            })
            logger.error(f"   ❌ Failed: {last_error}")
    
    logger.info(f"\n📊 Download complete: {summary['downloaded']} succeeded, "
               f"{summary['failed']} failed, {summary['skipped']} skipped")
    
    return summary


def download_slc_products(
    df: pd.DataFrame,
    config: InSARConfig
) -> Dict[str, Any]:
    """
    Download SLC products with retry logic and validation.
    
    Args:
        df: DataFrame with SLC products to download.
        config: InSAR configuration.
        
    Returns:
        Dict containing download summary.
    """
    if df is None or df.empty:
        logger.warning("No SLC products to download")
        return {'downloaded': 0, 'failed': 0, 'skipped': 0, 'details': []}
    
    # Ensure output directory exists
    abs_output_dir = os.path.abspath(config.download.output_dir)
    os.makedirs(abs_output_dir, exist_ok=True)
    
    logger.info(f"📥 Starting SLC download to: {abs_output_dir}")
    
    summary = {
        'downloaded': 0,
        'failed': 0,
        'skipped': 0,
        'details': []
    }
    
    total = len(df)
    for idx, row in df.iterrows():
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
        
        # Check if already downloaded
        product_dir = os.path.join(abs_output_dir, product_name)
        manifest_path = os.path.join(product_dir, 'manifest.safe')
        
        if config.download.resume_incomplete and os.path.exists(manifest_path):
            logger.info(f"   ⏭️  Skipping {idx + 1}/{total} (already exists)")
            summary['skipped'] += 1
            summary['details'].append({
                'name': product_name,
                'status': 'skipped',
                'reason': 'already_exists'
            })
            continue
        
        logger.info(f"📥 Downloading {idx + 1}/{total}: {product_name}...")
        
        success = False
        last_error = None
        
        for attempt in range(config.download.retry_count):
            try:
                pull_down(
                    s3_path=s3_path,
                    output_dir=abs_output_dir,
                    config_file=config.download.config_file,
                    total_size=content_length,
                    show_progress=True
                )
                
                # Validate download
                if config.download.validate_downloads:
                    if not os.path.isdir(product_dir):
                        raise ValueError(f"Product directory not found: {product_dir}")
                    if not os.path.exists(manifest_path):
                        raise ValueError("manifest.safe not found - download may be incomplete")
                
                success = True
                break
                
            except Exception as e:
                last_error = str(e)
                if attempt < config.download.retry_count - 1:
                    logger.warning(f"   ⚠️  Attempt {attempt + 1} failed, retrying...")
        
        if success:
            summary['downloaded'] += 1
            summary['details'].append({
                'name': product_name,
                'status': 'success'
            })
            logger.info(f"   ✅ Downloaded successfully")
        else:
            summary['failed'] += 1
            summary['details'].append({
                'name': product_name,
                'status': 'failed',
                'error': last_error
            })
            logger.error(f"   ❌ Failed: {last_error}")
    
    logger.info(f"\n📊 Download complete: {summary['downloaded']} succeeded, "
               f"{summary['failed']} failed, {summary['skipped']} skipped")
    
    return summary


# =============================================================================
# Main Workflow
# =============================================================================

def run_insar_workflow(
    config: InSARConfig,
    dry_run: bool = False,
    find_optimal: bool = False,
    download: bool = False
) -> Dict[str, Any]:
    """
    Execute the complete InSAR data acquisition workflow.
    
    Args:
        config: InSAR configuration.
        dry_run: If True, only search and report without downloading.
        find_optimal: If True, find optimal orbit configuration.
        download: If True, download the data.
        
    Returns:
        Dict containing workflow results.
    """
    results = {
        'config': {
            'mode': config.search.mode,
            'aoi_wkt': config.search.aoi_wkt[:50] + '...',
            'date_range': f"{config.search.start_date} to {config.search.end_date}"
        },
        'orbit_analysis': None,
        'search_results': None,
        'statistics': None,
        'download_summary': None
    }
    
    # Create output directories
    os.makedirs(config.download.output_dir, exist_ok=True)
    os.makedirs(config.output_statistics, exist_ok=True)
    
    # Initialize searcher
    searcher = CopernicusDataSearcher()
    
    # Step 1: Determine orbit configuration
    orbit_direction = config.search.orbit_direction
    relative_orbit = config.search.relative_orbit
    
    if find_optimal or (orbit_direction is None and relative_orbit is None):
        # Find optimal orbit
        orbit_analysis = find_optimal_orbit(config, searcher)
        results['orbit_analysis'] = orbit_analysis
        
        if orbit_analysis['recommended']:
            if orbit_direction is None:
                orbit_direction = orbit_analysis['recommended']['orbit_direction']
            if relative_orbit is None:
                relative_orbit = orbit_analysis['recommended']['relative_orbit']
    elif orbit_direction is None:
        # Only relative orbit specified, detect direction from regional preference
        orbit_direction = get_recommended_orbit_direction(config.search.aoi_wkt)
        logger.info(f"🧭 Auto-detected orbit direction: {orbit_direction}")
    
    logger.info(f"📡 Using: {orbit_direction} orbit, track #{relative_orbit}")
    
    # Ensure orbit_direction is set (fallback to DESCENDING if still None)
    if orbit_direction is None:
        orbit_direction = 'DESCENDING'
        logger.warning("⚠️  Could not determine orbit direction, defaulting to DESCENDING")
    
    # Step 2: Search for data
    if config.search.mode == 'burst':
        df = find_optimal_bursts(config, searcher, orbit_direction, relative_orbit)
    else:
        df = search_slc_products(config, searcher, orbit_direction, relative_orbit)
    
    if df.empty:
        logger.error("❌ No data found matching the search criteria")
        return results
    
    results['search_results'] = {
        'count': len(df),
        'columns': list(df.columns)
    }
    
    # Save results CSV
    if config.save_results_csv:
        csv_path = os.path.join(config.output_statistics, 'search_results.csv')
        df.to_csv(csv_path, index=False)
        logger.info(f"💾 Search results saved to: {csv_path}")
    
    # Step 3: Compute and save statistics
    stats = compute_temporal_statistics(df)
    results['statistics'] = stats
    
    if stats:
        logger.info("\n📊 TEMPORAL STATISTICS:")
        logger.info(f"   Total acquisitions: {stats['total_acquisitions']}")
        logger.info(f"   Date range: {stats['date_range']['start']} to {stats['date_range']['end']}")
        logger.info(f"   Span: {stats['date_range']['span_days']} days")
        
        if stats.get('temporal_gaps'):
            gaps = stats['temporal_gaps']
            logger.info(f"\n   Revisit intervals:")
            logger.info(f"     Min: {gaps['min_days']:.1f} days")
            logger.info(f"     Max: {gaps['max_days']:.1f} days")
            logger.info(f"     Mean: {gaps['mean_days']:.1f} days")
            logger.info(f"     Median: {gaps['median_days']:.1f} days")
        
        # Save statistics JSON
        stats_path = os.path.join(config.output_statistics, 'temporal_statistics.json')
        with open(stats_path, 'w') as f:
            json.dump(stats, f, indent=2)
        logger.info(f"\n💾 Statistics saved to: {stats_path}")
        
        # Create temporal plot
        plot_path = os.path.join(config.output_statistics, 'temporal_distribution.png')
        plot_temporal_distribution(df, plot_path)
    
    # Step 4: Download (if requested and not dry run)
    if download and not dry_run:
        if config.search.mode == 'burst':
            download_summary = download_bursts(df, config, searcher)
        else:
            download_summary = download_slc_products(df, config)
        
        results['download_summary'] = download_summary
    elif dry_run:
        logger.info("\n🔍 DRY RUN: Skipping download")
        logger.info(f"   Would download {len(df)} products to: {config.download.output_dir}")
    
    logger.info("\n✅ Workflow completed successfully!")
    
    return results


# =============================================================================
# CLI Entry Point
# =============================================================================

def main():
    """Main entry point for CLI usage."""
    parser = argparse.ArgumentParser(
        description='InSAR Data Acquisition Script - Sentinel-1 SLC/Burst downloader',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python insar.py config.yaml                  # Search and show results
  python insar.py config.yaml --dry-run        # Search without downloading
  python insar.py config.yaml --find-optimal   # Find optimal orbit configuration
  python insar.py config.yaml --download       # Search and download data
  python insar.py --create-config              # Create sample configuration file
        """
    )
    
    parser.add_argument(
        'config',
        nargs='?',
        help='Path to YAML configuration file'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Search and report without downloading'
    )
    
    parser.add_argument(
        '--find-optimal',
        action='store_true',
        help='Find optimal orbit configuration for the AOI'
    )
    
    parser.add_argument(
        '--download',
        action='store_true',
        help='Download the data after searching'
    )
    
    parser.add_argument(
        '--create-config',
        action='store_true',
        help='Create a sample configuration file'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create sample config if requested
    if args.create_config:
        create_sample_config()
        return 0
    
    # Validate config path
    if not args.config:
        parser.error("Configuration file is required (or use --create-config)")
    
    try:
        # Load configuration
        config = load_config(args.config)
        
        # Run workflow
        results = run_insar_workflow(
            config=config,
            dry_run=args.dry_run,
            find_optimal=args.find_optimal,
            download=args.download
        )
        
        return 0
        
    except FileNotFoundError as e:
        logger.error(f"❌ {e}")
        return 1
    except ValueError as e:
        logger.error(f"❌ Configuration error: {e}")
        return 1
    except Exception as e:
        logger.exception(f"❌ Unexpected error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
