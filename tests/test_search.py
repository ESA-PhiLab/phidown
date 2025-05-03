import pytest
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


from phidown.search import CopernicusDataSearcher

# Define the path to the config file relative to the test file
CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', 'phidown', 'config.json')


# Test successful initialization with default values
def test_searcher_init_defaults():
    searcher = CopernicusDataSearcher(config_path=CONFIG_PATH, collection_name='SENTINEL-1', product_type='SLC')
    assert searcher.base_url == "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"
    assert searcher.collection_name == 'SENTINEL-1'
    assert searcher.product_type == 'SLC'
    assert searcher.top == 1000
    assert searcher.order_by == "ContentDate/Start desc"


# Test initialization with custom values
def test_searcher_init_custom():
    searcher = CopernicusDataSearcher(
        config_path=CONFIG_PATH,
        collection_name='SENTINEL-2',
        product_type='S2MSI1C',
        orbit_direction='DESCENDING',
        cloud_cover_threshold=10.5,
        aoi_wkt='POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))',
        start_date='2023-01-01T00:00:00.000Z',
        end_date='2023-01-31T23:59:59.000Z',
        top=50,
        order_by="PublicationDate asc"
    )
    assert searcher.collection_name == 'SENTINEL-2'
    assert searcher.product_type == 'S2MSI1C'
    assert searcher.orbit_direction == 'DESCENDING'
    assert searcher.cloud_cover_threshold == 10.5
    assert searcher.aoi_wkt == 'POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))'
    assert searcher.start_date == '2023-01-01T00:00:00.000Z'
    assert searcher.end_date == '2023-01-31T23:59:59.000Z'
    assert searcher.top == 50
    assert searcher.order_by == "PublicationDate asc"


# Test invalid collection name
def test_searcher_invalid_collection():
    with pytest.raises(ValueError, match="Invalid collection name"):
        CopernicusDataSearcher(config_path=CONFIG_PATH, collection_name='INVALID-COLLECTION', product_type='SLC')


# Test invalid product type for a valid collection
def test_searcher_invalid_product_type():
    with pytest.raises(ValueError, match="Invalid product type"):
        CopernicusDataSearcher(config_path=CONFIG_PATH, collection_name='SENTINEL-1', product_type='INVALID-TYPE')


# Test invalid orbit direction
def test_searcher_invalid_orbit_direction():
    with pytest.raises(ValueError, match="Invalid orbit direction"):
        CopernicusDataSearcher(
            config_path=CONFIG_PATH,
            collection_name='SENTINEL-1',
            product_type='SLC',
            orbit_direction='INVALID'
        )


# Test invalid cloud cover threshold (below 0)
def test_searcher_invalid_cloud_cover_low():
    with pytest.raises(ValueError, match="must be between 0 and 100"):
        CopernicusDataSearcher(
            config_path=CONFIG_PATH,
            collection_name='SENTINEL-2',
            product_type='S2MSI1C',
            cloud_cover_threshold=-10
        )


# Test invalid cloud cover threshold (above 100)
def test_searcher_invalid_cloud_cover_high():
    with pytest.raises(ValueError, match="must be between 0 and 100"):
        CopernicusDataSearcher(
            config_path=CONFIG_PATH,
            collection_name='SENTINEL-2',
            product_type='S2MSI1C',
            cloud_cover_threshold=110
        )


# Test invalid AOI WKT format
def test_searcher_invalid_aoi_wkt_format():
    with pytest.raises(ValueError, match="must be a valid WKT POLYGON"):
        CopernicusDataSearcher(
            config_path=CONFIG_PATH,
            collection_name='SENTINEL-1',
            product_type='SLC',
            aoi_wkt='INVALID WKT'
        )


# Test invalid AOI WKT polygon (start/end points differ)
def test_searcher_invalid_aoi_wkt_polygon():
    with pytest.raises(ValueError, match="must start and end with the same point"):
        CopernicusDataSearcher(
            config_path=CONFIG_PATH,
            collection_name='SENTINEL-1',
            product_type='SLC',
            aoi_wkt='POLYGON((0 0, 1 0, 1 1, 0 1))'
        )


# Test invalid 'top' value (below 1)
def test_searcher_invalid_top_low():
    with pytest.raises(ValueError, match="must be between 1 and 1000"):
        CopernicusDataSearcher(config_path=CONFIG_PATH, collection_name='SENTINEL-1', product_type='SLC', top=0)


# Test invalid 'top' value (above 1000)
def test_searcher_invalid_top_high():
    with pytest.raises(ValueError, match="must be between 1 and 1000"):
        CopernicusDataSearcher(
            config_path=CONFIG_PATH,
            collection_name='SENTINEL-1',
            product_type='SLC',
            top=1001
        )


# Test invalid 'order_by' format
def test_searcher_invalid_order_by_format():
    with pytest.raises(ValueError, match="Invalid order_by format"):
        CopernicusDataSearcher(
            config_path=CONFIG_PATH,
            collection_name='SENTINEL-1',
            product_type='SLC',
            order_by='InvalidFormat'
        )


# Test invalid 'order_by' field
def test_searcher_invalid_order_by_field():
    with pytest.raises(ValueError, match="Invalid order_by value"):
        CopernicusDataSearcher(
            config_path=CONFIG_PATH,
            collection_name='SENTINEL-1',
            product_type='SLC',
            order_by='InvalidField desc'
        )


# Test invalid 'order_by' direction
def test_searcher_invalid_order_by_direction():
    with pytest.raises(ValueError, match="Invalid order_by value"):
        CopernicusDataSearcher(
            config_path=CONFIG_PATH,
            collection_name='SENTINEL-1',
            product_type='SLC',
            order_by='PublicationDate invalid'
        )


# Test building a basic filter
def test_build_filter_basic():
    searcher = CopernicusDataSearcher(config_path=CONFIG_PATH, collection_name='SENTINEL-1', product_type='SLC')
    searcher._build_filter()
    expected_filter = (
        "(Collection/Name eq 'SENTINEL-1') and "
        "Attributes/OData.CSC.StringAttribute/any(att:att/Name eq 'productType' "
        "and att/OData.CSC.StringAttribute/Value eq 'SLC')"
    )
    assert searcher.filter_condition == expected_filter


# Test building a complex filter
def test_build_filter_complex():
    searcher = CopernicusDataSearcher(
        config_path=CONFIG_PATH,
        collection_name='SENTINEL-2',
        product_type='S2MSI1C',
        orbit_direction='ASCENDING',
        cloud_cover_threshold=20,
        aoi_wkt='POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))',
        start_date='2023-01-01T00:00:00.000Z',
        end_date='2023-01-31T23:59:59.000Z',
        attributes={'platformSerialIdentifier': 'B'}
    )
    searcher._build_filter()
    expected_parts = [
        "(Collection/Name eq 'SENTINEL-2')",
        "Attributes/OData.CSC.StringAttribute/any(att:att/Name eq 'productType' "
        "and att/OData.CSC.StringAttribute/Value eq 'S2MSI1C')",
        "Attributes/OData.CSC.StringAttribute/any(att:att/Name eq 'orbitDirection' "
        "and att/OData.CSC.StringAttribute/Value eq 'ASCENDING')",
        "Attributes/OData.CSC.DoubleAttribute/any(att:att/Name eq 'cloudCover' "
        "and att/OData.CSC.DoubleAttribute/Value lt 20)",
        "geo.intersects(GeoFootprint, geography'POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))')",
        "ContentDate/Start ge 2023-01-01T00:00:00.000Z",
        "ContentDate/Start lt 2023-01-31T23:59:59.000Z",
        "Attributes/OData.CSC.StringAttribute/any(att:att/Name eq 'platformSerialIdentifier' "
        "and att/OData.CSC.StringAttribute/Value eq 'B')"
    ]
    # Check if all expected parts are in the generated filter condition
    for part in expected_parts:
        assert part in searcher.filter_condition
    # Check the structure (all parts joined by ' and ')
    assert searcher.filter_condition.count(' and ') == len(expected_parts) - 1


# Test building the full query URL
def test_build_query():
    searcher = CopernicusDataSearcher(config_path=CONFIG_PATH, collection_name='SENTINEL-1', product_type='GRD', top=10)
    url = searcher._build_query()
    expected_filter = (
        "(Collection/Name eq 'SENTINEL-1') and "
        "Attributes/OData.CSC.StringAttribute/any(att:att/Name eq 'productType' "
        "and att/OData.CSC.StringAttribute/Value eq 'GRD')"
    )
    expected_url = (
        f"{searcher.base_url}?$filter={expected_filter}"
        f"&$orderby={searcher.order_by}&$top={searcher.top}&$expand=Attributes"
    )
    assert url == expected_url

# Add more tests for execute_query and display_results using mocking (pytest-mock)
# These would involve mocking the 'requests.get' call and the pandas DataFrame creation.
