"""
Tests for Sentinel-1 SLC Burst mode functionality.
"""

import pytest
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from phidown.search import CopernicusDataSearcher

# Define the path to the config file relative to the test file
CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', 'phidown', 'config.json')


class TestBurstModeInitialization:
    """Test burst mode initialization and parameter setting."""
    
    def test_burst_mode_enabled(self):
        """Test that burst mode can be enabled."""
        searcher = CopernicusDataSearcher()
        searcher.query_by_filter(burst_mode=True)
        assert searcher.burst_mode is True
        assert searcher.base_url == 'https://catalogue.dataspace.copernicus.eu/odata/v1/Bursts'
    
    def test_burst_mode_disabled_default(self):
        """Test that burst mode is disabled by default."""
        searcher = CopernicusDataSearcher()
        searcher.query_by_filter(collection_name='SENTINEL-1', product_type='SLC')
        assert searcher.burst_mode is False
        assert searcher.base_url == 'https://catalogue.dataspace.copernicus.eu/odata/v1/Products'
    
    def test_burst_mode_with_basic_filters(self):
        """Test burst mode with basic temporal and spatial filters."""
        searcher = CopernicusDataSearcher()
        searcher.query_by_filter(
            burst_mode=True,
            start_date='2024-08-01T00:00:00.000Z',
            end_date='2024-08-15T00:00:00.000Z',
            aoi_wkt='POLYGON((12.655118166047592 47.44667197521409, 21.39065656328509 48.347694733853245, 28.334291357162826 41.877123516783655, 17.47086198383573 40.35854475076158, 12.655118166047592 47.44667197521409))'
        )
        assert searcher.burst_mode is True
        assert searcher.start_date == '2024-08-01T00:00:00.000Z'
        assert searcher.end_date == '2024-08-15T00:00:00.000Z'
        assert searcher.aoi_wkt is not None


class TestBurstModeParameters:
    """Test burst-specific parameter validation."""
    
    def test_valid_burst_id(self):
        """Test valid burst_id parameter."""
        searcher = CopernicusDataSearcher()
        searcher.query_by_filter(
            burst_mode=True,
            burst_id=15804,
            start_date='2024-08-01T00:00:00.000Z',
            end_date='2024-08-15T00:00:00.000Z'
        )
        assert searcher.burst_id == 15804
    
    def test_valid_absolute_burst_id(self):
        """Test valid absolute_burst_id parameter."""
        searcher = CopernicusDataSearcher()
        searcher.query_by_filter(
            burst_mode=True,
            absolute_burst_id=118199090,
            start_date='2024-08-01T00:00:00.000Z',
            end_date='2024-08-15T00:00:00.000Z'
        )
        assert searcher.absolute_burst_id == 118199090
    
    def test_valid_swath_identifier(self):
        """Test valid swath_identifier parameter."""
        for swath in ['IW1', 'IW2', 'IW3', 'EW1', 'EW2', 'EW3', 'EW4', 'EW5']:
            searcher = CopernicusDataSearcher()
            searcher.query_by_filter(
                burst_mode=True,
                swath_identifier=swath,
                start_date='2024-08-01T00:00:00.000Z',
                end_date='2024-08-15T00:00:00.000Z'
            )
            assert searcher.swath_identifier == swath
    
    def test_invalid_swath_identifier(self):
        """Test invalid swath_identifier parameter."""
        searcher = CopernicusDataSearcher()
        with pytest.raises(ValueError, match='Invalid swath_identifier'):
            searcher.query_by_filter(
                burst_mode=True,
                swath_identifier='INVALID',
                start_date='2024-08-01T00:00:00.000Z',
                end_date='2024-08-15T00:00:00.000Z'
            )
    
    def test_valid_parent_product_type(self):
        """Test valid parent_product_type parameter."""
        for ptype in ['IW_SLC__1S', 'EW_SLC__1S']:
            searcher = CopernicusDataSearcher()
            searcher.query_by_filter(
                burst_mode=True,
                parent_product_type=ptype,
                start_date='2024-08-01T00:00:00.000Z',
                end_date='2024-08-15T00:00:00.000Z'
            )
            assert searcher.parent_product_type == ptype
    
    def test_invalid_parent_product_type(self):
        """Test invalid parent_product_type parameter."""
        searcher = CopernicusDataSearcher()
        with pytest.raises(ValueError, match='Invalid parent_product_type'):
            searcher.query_by_filter(
                burst_mode=True,
                parent_product_type='INVALID_TYPE',
                start_date='2024-08-01T00:00:00.000Z',
                end_date='2024-08-15T00:00:00.000Z'
            )
    
    def test_valid_operational_mode(self):
        """Test valid operational_mode parameter."""
        for mode in ['IW', 'EW']:
            searcher = CopernicusDataSearcher()
            searcher.query_by_filter(
                burst_mode=True,
                operational_mode=mode,
                start_date='2024-08-01T00:00:00.000Z',
                end_date='2024-08-15T00:00:00.000Z'
            )
            assert searcher.operational_mode == mode
    
    def test_invalid_operational_mode(self):
        """Test invalid operational_mode parameter."""
        searcher = CopernicusDataSearcher()
        with pytest.raises(ValueError, match='Invalid operational_mode'):
            searcher.query_by_filter(
                burst_mode=True,
                operational_mode='INVALID',
                start_date='2024-08-01T00:00:00.000Z',
                end_date='2024-08-15T00:00:00.000Z'
            )
    
    def test_valid_polarisation_channels(self):
        """Test valid polarisation_channels parameter."""
        for pol in ['VV', 'VH', 'HH', 'HV']:
            searcher = CopernicusDataSearcher()
            searcher.query_by_filter(
                burst_mode=True,
                polarisation_channels=pol,
                start_date='2024-08-01T00:00:00.000Z',
                end_date='2024-08-15T00:00:00.000Z'
            )
            assert searcher.polarisation_channels == pol
    
    def test_invalid_polarisation_channels(self):
        """Test invalid polarisation_channels parameter."""
        searcher = CopernicusDataSearcher()
        with pytest.raises(ValueError, match='Invalid polarisation_channels'):
            searcher.query_by_filter(
                burst_mode=True,
                polarisation_channels='XX',
                start_date='2024-08-01T00:00:00.000Z',
                end_date='2024-08-15T00:00:00.000Z'
            )
    
    def test_valid_platform_serial_identifier(self):
        """Test valid platform_serial_identifier parameter."""
        for platform in ['A', 'B', 'C']:
            searcher = CopernicusDataSearcher()
            searcher.query_by_filter(
                burst_mode=True,
                platform_serial_identifier=platform,
                start_date='2024-08-01T00:00:00.000Z',
                end_date='2024-08-15T00:00:00.000Z'
            )
            assert searcher.platform_serial_identifier == platform
    
    def test_invalid_platform_serial_identifier(self):
        """Test invalid platform_serial_identifier parameter."""
        searcher = CopernicusDataSearcher()
        with pytest.raises(ValueError, match='Invalid platform_serial_identifier'):
            searcher.query_by_filter(
                burst_mode=True,
                platform_serial_identifier='D',
                start_date='2024-08-01T00:00:00.000Z',
                end_date='2024-08-15T00:00:00.000Z'
            )
    
    def test_parent_product_name(self):
        """Test parent_product_name parameter."""
        searcher = CopernicusDataSearcher()
        product_name = 'S1A_IW_SLC__1SDV_20240802T060719_20240802T060746_055030_06B44E_E7CC.SAFE'
        searcher.query_by_filter(
            burst_mode=True,
            parent_product_name=product_name,
            start_date='2024-08-01T00:00:00.000Z',
            end_date='2024-08-15T00:00:00.000Z'
        )
        assert searcher.parent_product_name == product_name
    
    def test_parent_product_id(self):
        """Test parent_product_id parameter."""
        searcher = CopernicusDataSearcher()
        product_id = 'e463365f-728b-4890-b123-97c76941c878'
        searcher.query_by_filter(
            burst_mode=True,
            parent_product_id=product_id,
            start_date='2024-08-01T00:00:00.000Z',
            end_date='2024-08-15T00:00:00.000Z'
        )
        assert searcher.parent_product_id == product_id
    
    def test_datatake_id(self):
        """Test datatake_id parameter."""
        searcher = CopernicusDataSearcher()
        searcher.query_by_filter(
            burst_mode=True,
            datatake_id=40352,
            start_date='2024-08-01T00:00:00.000Z',
            end_date='2024-08-15T00:00:00.000Z'
        )
        assert searcher.datatake_id == 40352
    
    def test_relative_orbit_number(self):
        """Test relative_orbit_number parameter."""
        searcher = CopernicusDataSearcher()
        searcher.query_by_filter(
            burst_mode=True,
            relative_orbit_number=8,
            start_date='2024-08-01T00:00:00.000Z',
            end_date='2024-08-15T00:00:00.000Z'
        )
        assert searcher.relative_orbit_number == 8
    
    def test_invalid_burst_id_type(self):
        """Test that burst_id must be an integer."""
        searcher = CopernicusDataSearcher()
        with pytest.raises(TypeError, match='burst_id must be an integer'):
            searcher.query_by_filter(
                burst_mode=True,
                burst_id='not_an_integer',
                start_date='2024-08-01T00:00:00.000Z',
                end_date='2024-08-15T00:00:00.000Z'
            )
    
    def test_invalid_absolute_burst_id_type(self):
        """Test that absolute_burst_id must be an integer."""
        searcher = CopernicusDataSearcher()
        with pytest.raises(TypeError, match='absolute_burst_id must be an integer'):
            searcher.query_by_filter(
                burst_mode=True,
                absolute_burst_id='not_an_integer',
                start_date='2024-08-01T00:00:00.000Z',
                end_date='2024-08-15T00:00:00.000Z'
            )
    
    def test_invalid_datatake_id_type(self):
        """Test that datatake_id must be an integer."""
        searcher = CopernicusDataSearcher()
        with pytest.raises(TypeError, match='datatake_id must be an integer'):
            searcher.query_by_filter(
                burst_mode=True,
                datatake_id='not_an_integer',
                start_date='2024-08-01T00:00:00.000Z',
                end_date='2024-08-15T00:00:00.000Z'
            )
    
    def test_invalid_relative_orbit_number_type(self):
        """Test that relative_orbit_number must be an integer."""
        searcher = CopernicusDataSearcher()
        with pytest.raises(TypeError, match='relative_orbit_number must be an integer'):
            searcher.query_by_filter(
                burst_mode=True,
                relative_orbit_number='not_an_integer',
                start_date='2024-08-01T00:00:00.000Z',
                end_date='2024-08-15T00:00:00.000Z'
            )


class TestBurstModeFilterBuilding:
    """Test filter building for burst mode."""
    
    def test_build_filter_with_burst_id(self):
        """Test filter building with burst_id."""
        searcher = CopernicusDataSearcher()
        searcher.query_by_filter(
            burst_mode=True,
            burst_id=15804,
            start_date='2024-08-01T00:00:00.000Z',
            end_date='2024-08-15T00:00:00.000Z'
        )
        searcher._build_filter()
        assert 'BurstId eq 15804' in searcher.filter_condition
        assert 'ContentDate/Start ge 2024-08-01T00:00:00.000Z' in searcher.filter_condition
        assert 'ContentDate/Start le 2024-08-15T00:00:00.000Z' in searcher.filter_condition
    
    def test_build_filter_with_swath_identifier(self):
        """Test filter building with swath_identifier."""
        searcher = CopernicusDataSearcher()
        searcher.query_by_filter(
            burst_mode=True,
            swath_identifier='IW2',
            start_date='2024-08-01T00:00:00.000Z',
            end_date='2024-08-15T00:00:00.000Z'
        )
        searcher._build_filter()
        assert "SwathIdentifier eq 'IW2'" in searcher.filter_condition
    
    def test_build_filter_with_parent_product_type(self):
        """Test filter building with parent_product_type."""
        searcher = CopernicusDataSearcher()
        searcher.query_by_filter(
            burst_mode=True,
            parent_product_type='IW_SLC__1S',
            start_date='2024-08-01T00:00:00.000Z',
            end_date='2024-08-15T00:00:00.000Z'
        )
        searcher._build_filter()
        assert "ParentProductType eq 'IW_SLC__1S'" in searcher.filter_condition
    
    def test_build_filter_with_polarisation_channels(self):
        """Test filter building with polarisation_channels."""
        searcher = CopernicusDataSearcher()
        searcher.query_by_filter(
            burst_mode=True,
            polarisation_channels='VV',
            start_date='2024-08-01T00:00:00.000Z',
            end_date='2024-08-15T00:00:00.000Z'
        )
        searcher._build_filter()
        assert "PolarisationChannels eq 'VV'" in searcher.filter_condition
    
    def test_build_filter_with_orbit_direction(self):
        """Test filter building with orbit_direction in burst mode."""
        searcher = CopernicusDataSearcher()
        searcher.query_by_filter(
            burst_mode=True,
            orbit_direction='DESCENDING',
            start_date='2024-08-01T00:00:00.000Z',
            end_date='2024-08-15T00:00:00.000Z'
        )
        searcher._build_filter()
        assert "OrbitDirection eq 'DESCENDING'" in searcher.filter_condition
    
    def test_build_filter_complex_burst(self):
        """Test filter building with multiple burst parameters."""
        searcher = CopernicusDataSearcher()
        searcher.query_by_filter(
            burst_mode=True,
            burst_id=15804,
            swath_identifier='IW2',
            parent_product_type='IW_SLC__1S',
            polarisation_channels='VV',
            orbit_direction='DESCENDING',
            start_date='2024-08-01T00:00:00.000Z',
            end_date='2024-08-15T00:00:00.000Z'
        )
        searcher._build_filter()
        assert 'BurstId eq 15804' in searcher.filter_condition
        assert "SwathIdentifier eq 'IW2'" in searcher.filter_condition
        assert "ParentProductType eq 'IW_SLC__1S'" in searcher.filter_condition
        assert "PolarisationChannels eq 'VV'" in searcher.filter_condition
        assert "OrbitDirection eq 'DESCENDING'" in searcher.filter_condition
    
    def test_build_filter_with_aoi(self):
        """Test filter building with AOI in burst mode."""
        searcher = CopernicusDataSearcher()
        aoi = 'POLYGON((12.655118166047592 47.44667197521409, 21.39065656328509 48.347694733853245, 28.334291357162826 41.877123516783655, 17.47086198383573 40.35854475076158, 12.655118166047592 47.44667197521409))'
        searcher.query_by_filter(
            burst_mode=True,
            aoi_wkt=aoi,
            start_date='2024-08-01T00:00:00.000Z',
            end_date='2024-08-15T00:00:00.000Z'
        )
        searcher._build_filter()
        assert 'OData.CSC.Intersects' in searcher.filter_condition
    
    def test_build_filter_with_parent_product_name(self):
        """Test filter building with parent_product_name."""
        searcher = CopernicusDataSearcher()
        product_name = 'S1A_IW_SLC__1SDV_20240802T060719_20240802T060746_055030_06B44E_E7CC.SAFE'
        searcher.query_by_filter(
            burst_mode=True,
            parent_product_name=product_name,
            start_date='2024-08-01T00:00:00.000Z',
            end_date='2024-08-15T00:00:00.000Z'
        )
        searcher._build_filter()
        assert f"ParentProductName eq '{product_name}'" in searcher.filter_condition


class TestBurstModeQueryBuilding:
    """Test query URL building for burst mode."""
    
    def test_build_query_burst_endpoint(self):
        """Test that burst mode uses the correct endpoint."""
        searcher = CopernicusDataSearcher()
        searcher.query_by_filter(
            burst_mode=True,
            burst_id=15804,
            start_date='2024-08-01T00:00:00.000Z',
            end_date='2024-08-15T00:00:00.000Z'
        )
        url = searcher._build_query()
        assert 'https://catalogue.dataspace.copernicus.eu/odata/v1/Bursts' in url
        assert '$expand=Attributes' not in url  # Burst mode should not expand attributes
    
    def test_build_query_non_burst_endpoint(self):
        """Test that non-burst mode uses the correct endpoint."""
        searcher = CopernicusDataSearcher()
        searcher.query_by_filter(
            collection_name='SENTINEL-1',
            product_type='SLC',
            start_date='2024-08-01T00:00:00.000Z',
            end_date='2024-08-15T00:00:00.000Z'
        )
        url = searcher._build_query()
        assert 'https://catalogue.dataspace.copernicus.eu/odata/v1/Products' in url
        assert '$expand=Attributes' in url  # Non-burst mode should expand attributes
    
    def test_build_query_with_count(self):
        """Test query building with count option in burst mode."""
        searcher = CopernicusDataSearcher()
        searcher.query_by_filter(
            burst_mode=True,
            burst_id=15804,
            start_date='2024-08-01T00:00:00.000Z',
            end_date='2024-08-15T00:00:00.000Z',
            count=True
        )
        url = searcher._build_query()
        assert '$count=true' in url
    
    def test_build_query_with_top_and_orderby(self):
        """Test query building with top and orderby in burst mode."""
        searcher = CopernicusDataSearcher()
        searcher.query_by_filter(
            burst_mode=True,
            burst_id=15804,
            start_date='2024-08-01T00:00:00.000Z',
            end_date='2024-08-15T00:00:00.000Z',
            top=50,
            order_by='ContentDate/Start desc'
        )
        url = searcher._build_query()
        assert '$top=50' in url
        assert '$orderby=ContentDate/Start desc' in url


class TestBurstModeBackwardCompatibility:
    """Test that burst mode doesn't break existing functionality."""
    
    def test_non_burst_mode_still_works(self):
        """Test that non-burst mode queries still work as before."""
        searcher = CopernicusDataSearcher()
        searcher.query_by_filter(
            collection_name='SENTINEL-1',
            product_type='SLC',
            orbit_direction='ASCENDING',
            start_date='2024-08-01T00:00:00.000Z',
            end_date='2024-08-15T00:00:00.000Z'
        )
        assert searcher.burst_mode is False
        assert searcher.collection_name == 'SENTINEL-1'
        assert searcher.product_type == 'SLC'
    
    def test_cloud_cover_ignored_in_burst_mode(self):
        """Test that cloud cover threshold is ignored in burst mode."""
        searcher = CopernicusDataSearcher()
        searcher.query_by_filter(
            burst_mode=True,
            cloud_cover_threshold=20,  # Should be ignored
            start_date='2024-08-01T00:00:00.000Z',
            end_date='2024-08-15T00:00:00.000Z'
        )
        searcher._build_filter()
        assert 'cloudCover' not in searcher.filter_condition
    
    def test_attributes_ignored_in_burst_mode(self):
        """Test that custom attributes are ignored in burst mode."""
        searcher = CopernicusDataSearcher()
        searcher.query_by_filter(
            burst_mode=True,
            attributes={'someAttribute': 'value'},  # Should be ignored
            start_date='2024-08-01T00:00:00.000Z',
            end_date='2024-08-15T00:00:00.000Z'
        )
        searcher._build_filter()
        # Should not raise validation error and should not include in filter
        assert searcher.filter_condition is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
