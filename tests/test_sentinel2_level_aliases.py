import os

import pytest

from phidown.search import CopernicusDataSearcher


CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "phidown", "config.json")


@pytest.mark.parametrize("alias", ["L1C", "Level-1C"])
def test_sentinel2_product_type_accepts_level_1c_aliases(alias):
    searcher = CopernicusDataSearcher(
        config_path=CONFIG_PATH,
        collection_name="SENTINEL-2",
        product_type=alias,
    )

    searcher._build_filter()

    assert searcher.product_type == "S2MSI1C"
    assert "Value eq 'S2MSI1C'" in searcher.filter_condition
    assert alias not in searcher.filter_condition


def test_sentinel2_product_type_accepts_level_2a_alias():
    searcher = CopernicusDataSearcher(
        config_path=CONFIG_PATH,
        collection_name="SENTINEL-2",
        product_type="Level-2A",
    )

    searcher._build_filter()

    assert searcher.product_type == "S2MSI2A"
    assert "Value eq 'S2MSI2A'" in searcher.filter_condition
    assert "Level-2A" not in searcher.filter_condition


def test_sentinel2_processing_level_attribute_uses_canonical_cdse_value():
    searcher = CopernicusDataSearcher(
        config_path=CONFIG_PATH,
        collection_name="SENTINEL-2",
        attributes={"processingLevel": "L2A"},
    )

    searcher._build_filter()

    assert searcher.attributes == {"processingLevel": "S2MSI2A"}
    assert "att/Name eq 'processingLevel'" in searcher.filter_condition
    assert "Value eq 'S2MSI2A'" in searcher.filter_condition
    assert "Value eq 'L2A'" not in searcher.filter_condition


def test_sentinel2_product_type_attribute_uses_canonical_cdse_value():
    searcher = CopernicusDataSearcher(
        config_path=CONFIG_PATH,
        collection_name="SENTINEL-2",
        attributes={"productType": "L1C"},
    )

    searcher._build_filter()

    assert searcher.attributes == {"productType": "S2MSI1C"}
    assert "att/Name eq 'productType'" in searcher.filter_condition
    assert "Value eq 'S2MSI1C'" in searcher.filter_condition


def test_non_sentinel2_product_type_does_not_accept_sentinel2_alias():
    with pytest.raises(ValueError, match="Invalid product type: L2A"):
        CopernicusDataSearcher(
            config_path=CONFIG_PATH,
            collection_name="SENTINEL-1",
            product_type="L2A",
        )
