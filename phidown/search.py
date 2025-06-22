import requests
import pandas as pd
import os
import json
import typing
from datetime import datetime
import copy 

from .downloader import pull_down

# Write the credentials in secret.yml!


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
    def __init__(self) -> None:
        """
        Initialize the CopernicusDataSearcher.
        Configuration is loaded from the default path.
        Call _query_by_filter() to set search parameters before executing a query.
        """
        self.base_url: str = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"
        self.config: typing.Optional[dict] = self._load_config()  # Load config from default path

        # Initialize attributes to be set by _query_by_filter
        self.collection_name: typing.Optional[str] = None
        self.product_type: typing.Optional[str] = None
        self.orbit_direction: typing.Optional[str] = None
        self.cloud_cover_threshold: typing.Optional[float] = None
        self.attributes: typing.Optional[typing.Dict[str, typing.Union[str, int, float]]] = None
        self.aoi_wkt: typing.Optional[str] = None
        self.start_date: typing.Optional[str] = None
        self.end_date: typing.Optional[str] = None
        
        # Set default values for top and order_by
        self.top: int = 1000
        self.count: bool = False
        self.order_by: str = "ContentDate/Start desc"

        # Initialize placeholders for query results
        self._initialize_placeholders()

    def query_by_filter(
        self,
        base_url: str = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products",
        collection_name: typing.Optional[str] = 'SENTINEL-1',
        product_type: typing.Optional[str] = None,
        orbit_direction: typing.Optional[str] = None,
        cloud_cover_threshold: typing.Optional[float] = None,
        attributes: typing.Optional[typing.Dict[str, typing.Union[str, int, float]]] = None,
        aoi_wkt: typing.Optional[str] = None,  # Disclaimers: Polygon must start and end with the same point. Coordinates must be given in EPSG 4326
        start_date: typing.Optional[str] = None,
        end_date: typing.Optional[str] = None,
        top: int = 1000,
        count: bool = False,  
        order_by: str = "ContentDate/Start desc"
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
            aoi_wkt (str, optional): Area of Interest in WKT format. Defaults to None.
            start_date (str, optional): Start date for filtering (ISO 8601 format). Defaults to None.
            end_date (str, optional): End date for filtering (ISO 8601 format). Defaults to None.
            top (int, optional): Maximum number of results to retrieve. Defaults to 1000.
            order_by (str, optional): Field and direction to order results by. Defaults to "ContentDate/Start desc".
        """
        self.base_url = base_url  # Set or override base_url
        self.count = count  # Set or override count option
        
        # Assign and validate parameters
        self.collection_name = collection_name
        self._validate_collection(self.collection_name) # Validate collection name

        self.product_type = product_type
        self._validate_product_type() # Validate product type (depends on collection_name and config)

        self.orbit_direction = orbit_direction
        self._validate_orbit_direction()

        self.cloud_cover_threshold = cloud_cover_threshold
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
        if self.attributes is not None:
            self._validate_attributes()
        # Note: _initialize_placeholders() is called in __init__ to ensure attributes exist.
        # If _query_by_filter is meant to reset for a brand new query, consider if it needs to be called here too.
        # For now, assuming execute_query will populate them based on new parameters.

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
            coordinates = [coord.strip() for coord in self.aoi_wkt[9:-2].split(",")]
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
        if self.collection_name:
            collection_filter = f"Collection/Name eq '{self.collection_name}'"
            filters.append(f"({collection_filter})")

    def _add_product_type_filter(self, filters):
        if self.product_type:
            filters.append(
                "Attributes/OData.CSC.StringAttribute/any(att:att/Name eq 'productType' "
                f"and att/OData.CSC.StringAttribute/Value eq '{self.product_type}')"
            )

    def _add_orbit_direction_filter(self, filters):
        if self.orbit_direction:
            filters.append(
                "Attributes/OData.CSC.StringAttribute/any(att:att/Name eq 'orbitDirection' "
                f"and att/OData.CSC.StringAttribute/Value eq '{self.orbit_direction}')"
            )

    def _add_cloud_cover_filter(self, filters):
        if self.cloud_cover_threshold is not None:
            filters.append(
                "Attributes/OData.CSC.DoubleAttribute/any(att:att/Name eq 'cloudCover' "
                f"and att/OData.CSC.DoubleAttribute/Value lt {self.cloud_cover_threshold})"
            )

    def _add_aoi_filter(self, filters):
        if self.aoi_wkt:
            filters.append(f"OData.CSC.Intersects(area=geography'SRID=4326;{self.aoi_wkt}')")

    def _add_date_filters(self, filters):
        if self.start_date:
            filters.append(f"ContentDate/Start ge {self.start_date}")
        if self.end_date:
            filters.append(f"ContentDate/Start lt {self.end_date}")

    def _add_attribute_filters(self, filters):
        if self.attributes:
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

        # Combine all filters into a single filter condition
        if not filters:
            raise ValueError("No valid filters provided. At least one filter is required.")

        self.filter_condition = " and ".join(filters)

    def _build_query(self):
        """Build the full OData query URL"""
        self._build_filter()
        self.query = f"?$filter={self.filter_condition}&$orderby={self.order_by}&$top={self.top}&$expand=Attributes"
        if self.count:
            self.query += "&$count=true"
        self.url = f"{self.base_url}{self.query}"
        return self.url

    def execute_query(self):
        """Execute the query and retrieve data"""
        url = self._build_query()
        self.response = copy.deepcopy(requests.get(url))
        self.response.raise_for_status()  # Raise an error for bad status codes

        self.json_data = self.response.json()
        self.num_results = self.json_data.get('@odata.count', 0)
        self.df = pd.DataFrame.from_dict(self.json_data['value'])

        return self.df

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
            self.response = requests.get(self.url)
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
            self.response = requests.get(self.url)
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
            columns = ['Id', 'Name', 'S3Path', 'GeoFootprint', 'OriginDate', 'Attributes']

        if 'OriginDate' in self.df.columns:
            self.df['OriginDate'] = pd.to_datetime(self.df['OriginDate']).dt.strftime('%Y-%m-%d %H:%M:%S')

        if not isinstance(columns, list):
            raise TypeError("Columns must be a list of strings")

        if self.df.empty:
            print("The DataFrame is empty.")
            return None
        else:
            return self.df[columns].head(top_n)

    def download_product(self, eo_product_name: str, output_dir: str, verbose=True):
        """
        Download the EO product using the downloader module.
        """
        res = self.query_by_name(eo_product_name)
        if res.empty:
            print(f"No product found with name: {eo_product_name}")
            return False
        
        # Ensure output_dir is an absolute path
        abs_output_dir = os.path.abspath(output_dir)

        if verbose:
            print(f"Downloading product: {eo_product_name}")
            print(f"Output directory: {abs_output_dir}")
        
        s3path = res['S3Path'].iloc[0]
        # Call the downloader function
        pull_down(s3path, 
                abs_output_dir,
                verbose=True)