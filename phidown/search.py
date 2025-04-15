import requests
import pandas as pd
import sys 
import os, json 
import typing
from datetime import datetime
# Write the credentials from config.json!

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

class CopernicusDataSearcher:
    def __init__(self, 
            base_url: str = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products",
            config_path: typing.Optional[str] = None,
            collection_names: typing.Optional[str] = ['SENTINEL-1'],
            product_type: typing.Optional[str] = None,
            orbit_direction: typing.Optional[str] = None,
            cloud_cover_threshold: typing.Optional[float] = None,
            aoi_wkt: typing.Optional[str] = None, 
            start_date: typing.Optional[str] = None,
            end_date: typing.Optional[str] = None,
            top: int = 1000,
            order_by: str = "ContentDate/Start desc"):
        """
        Initialize the CopernicusDataSearcher with default parameters.

        Args:
            base_url (str): The base URL for the OData API.
            config_path (str, optional): Path to the configuration file. Defaults to None.
            collection_names (List(str), optional): Name of the collection to search. Defaults to ['SENTINEL-1'].
            product_type (str, optional): Type of product to filter. Defaults to None.
            orbit_direction (str, optional): Orbit direction to filter (e.g., 'ASCENDING', 'DESCENDING'). Defaults to None.
            cloud_cover_threshold (float, optional): Maximum cloud cover percentage to filter. Defaults to None.
            aoi_wkt (str, optional): Area of Interest in WKT format. Disclaimers: Polygon must start and end with the same point. Coordinates must be given in EPSG 4326
            start_date (str, optional): Start date for filtering (ISO 8601 format). Defaults to None.
            end_date (str, optional): End date for filtering (ISO 8601 format). Defaults to None.
            top (int, optional): Maximum number of results to retrieve. Defaults to 100.
            order_by (str, optional): Field and direction to order results by. Defaults to "ContentDate/Start desc".
        """
        self.base_url: str = base_url
        self.config: typing.Optional[dict] = self._load_config(config_path)
        # Load configuration
        self._load_config(config_path)
        
        self.collection_names: typing.Optional[str] = collection_names
        for c in collection_names:
            self._validate_collection(c)
        
        self.product_type: typing.Optional[str] = product_type
        self._validate_product_type()
        
        self.orbit_direction: typing.Optional[str] = orbit_direction
        self._validate_orbit_direction()
        
        self.cloud_cover_threshold: typing.Optional[float] = cloud_cover_threshold
        self._validate_cloud_cover_threshold()
        
        self.aoi_wkt: typing.Optional[str] = aoi_wkt
        self._validate_aoi_wkt()
        
        self.start_date: typing.Optional[str] = start_date
        self.end_date: typing.Optional[str] = end_date
        
        
        self.top: int = top
        self._validate_top()
        
        self.order_by: str = order_by
        self._validate_order_by()
        

        
        # Placeholders for attributes to be set later
        self.filter_condition: typing.Optional[str] = None
        self.query: typing.Optional[str] = None
        self.url: typing.Optional[str] = None
        self.response: typing.Optional[requests.Response] = None
        self.json_data: typing.Optional[dict] = None
        self.df: typing.Optional[pd.DataFrame] = None
    
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


    def _get_valid_product_types(self, collection_names):
        """
        Extracts and filters valid product types from a configuration dictionary based on given collection names.

        Args:
            config (dict): A dictionary containing configuration data. It must include an 'attributes' key,
                        where each value is a dictionary that may contain a 'productType' key.
            collection_names (iterable): A collection of names to filter the product types. (e.g, SENTINEL-1, SENTINEL-2)

        Returns:
            tuple: A tuple containing:
                - valid_product_types (dict): A dictionary of product types filtered by the given collection names.
                - values (list): A flattened list of all product types from the configuration.
        """
        product_types = {key: value.get('productType', None) for key, value in self.config['attributes'].items()}
        valid_product_types = {key: value for key, value in product_types.items() if key in collection_names}
        return valid_product_types


    def _validate_product_type(self):
        """
        Validates the provided product type against a list of valid product types.
        Raises:
            ValueError: If the product type is None, empty, or not in the list of valid product types.
            TypeError: If the product type is not a string.
        """

        valid_product_types = self._get_valid_product_types(self.collection_names)
        if self.product_type is None:
            raise ValueError("Product type cannot be None")
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
            try:
                field, direction = self.order_by.split()
                if field in valid_order_by_fields and direction in valid_order_by_directions:
                    self.order_by = self.order_by
                else:
                    raise ValueError(
                        f"Invalid order_by value: {self.order_by}. Must be one of: "
                        f"{', '.join([f'{f} {d}' for f in valid_order_by_fields for d in valid_order_by_directions])}"
                    )
            except ValueError:
                raise ValueError(
                    f"Invalid order_by format: {self.order_by}. It must be in the format 'field direction'."
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
        valid_orbit_directions = ["ASCENDING", "DESCENDING"]
        if self.orbit_direction is not None and self.orbit_direction not in valid_orbit_directions:
            raise ValueError(
                f"Invalid orbit direction: {self.orbit_direction}. Must be one of: {', '.join(valid_orbit_directions)}"
            )


    def _validate_aoi_wkt(self):
        """
        Validate the 'aoi_wkt' parameter to ensure it is a valid WKT polygon.

        Raises:
            ValueError: If the 'aoi_wkt' parameter is not a valid WKT polygon.
        """
        if self.aoi_wkt is not None:
            if not isinstance(self.aoi_wkt, str):
                raise TypeError("The 'aoi_wkt' parameter must be a string")
            if not self.aoi_wkt.strip():
                raise ValueError("The 'aoi_wkt' parameter cannot be empty")
            if not (self.aoi_wkt.startswith("POLYGON((") and self.aoi_wkt.endswith("))")):
                raise ValueError("The 'aoi_wkt' parameter must be a valid WKT POLYGON")
            coordinates = self.aoi_wkt[9:-2].split(",")
            if coordinates[0] != coordinates[-1]:
                raise ValueError("The 'aoi_wkt' polygon must start and end with the same point")


    def _validate_time(self):
        """
        Validate the 'start_date' and 'end_date' parameters to ensure they are in ISO 8601 format
        and that the start date is earlier than the end date.

        Raises:
            ValueError: If the dates are not in ISO 8601 format or if the start date is not earlier than the end date.
        """

        def is_iso8601(date_str):
            try:
                datetime.fromisoformat(date_str)
                return True
            except ValueError:
                return False

        if self.start_date:
            if not is_iso8601(self.start_date):
                raise ValueError(f"Invalid start_date format: {self.start_date}. Must be in ISO 8601 format.")
        if self.end_date:
            if not is_iso8601(self.end_date):
                raise ValueError(f"Invalid end_date format: {self.end_date}. Must be in ISO 8601 format.")
        if self.start_date and self.end_date:
            if self.start_date >= self.end_date:
                raise ValueError("start_date must be earlier than end_date.")


    def build_query(self):
        """Build the full OData query URL"""
        self.build_filter()
        self.query = f"?$filter={self.filter_condition}&$orderby={self.order_by}&$top={self.top}&$expand=Attributes"
        self.url = f"{self.base_url}{self.query}"
        return self.url


    def execute_query(self):
        """Execute the query and retrieve data"""
        self.build_query()
        self.response = requests.get(self.url)
        self.response.raise_for_status()  # Raise an error for bad status codes
        
        self.json_data = self.response.json()
        self.df = pd.DataFrame.from_dict(self.json_data['value'])
        
        return self.df


    def display_results(self, columns=None):
        """Display the query results with selected columns"""
        if self.df is None:
            self.execute_query()
            
        if columns is None:
            columns = ['Id', 'Name', 'S3Path', 'GeoFootprint']
            
        return self.df[columns]

