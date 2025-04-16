# SentinelAPI: Sentinel Data Management Tool

This repository provides tools for managing Sentinel data using AWS services and dataset tools. It includes functionality for authentication, product search, and downloading Earth Observation (EO) products.

> **⚠️ Search Optimization Tips**  
>  
> Crucial for the search performance is specifying the collection name. Example:  
> `Collection/Name eq 'SENTINEL-3'`.  
>  
> An additional efficient way to accelerate the query performance is limiting the query by acquisition dates, e.g.:  
> `ContentDate/Start gt 2022-05-03T00:00:00.000Z and ContentDate/Start lt 2022-05-21T00:00:00.000Z`.  
>  
> When searching for products and adding a wide range of dates to the query, e.g., from 2017 to 2023, we recommend splitting the query into individual years, e.g., from January 1, 2023, to December 31, 2023.

---
## Features

- Authenticate with the Copernicus Data Space Ecosystem.
- Search for Sentinel products using the OData API.
- Download Sentinel products using the S3 protocol.

---

## Prerequisites
- Python 3.8 or higher

---

## Installation

### Step 1: Install PDM
- [PDM](https://pdm.fming.dev/) (Python Dependency Manager). We gonna use pdm to simplify our life. 
If you don't already have PDM installed, install it via pip:
```bash
pip install pdm
```

### Step 2: Clone the Repository
```bash
git clone https://github.com/sirbastiano/phidown.git
cd phidown
```

### Step 3: Install Dependencies Using PDM
Use the `pdm.lock` file to install exact versions of dependencies:
```bash
pdm install
```

This ensures faster and consistent environment setup.

### Alternative: Install Dependencies Using pip
If you prefer using pip, you can install the dependencies directly:
```bash
pip install .
```

This will install the package and its dependencies as defined in the `pyproject.toml` file.

---

## Usage

### Run the Main Script
To search and download Sentinel products:
```bash
pdm run python phisenapi/main.py
```

### Example
The script will:
1. Authenticate with the Copernicus Data Space Ecosystem.
2. Search for Sentinel products within the specified AOI and date range.
3. Download the first matching product using S3.

---

## Project Structure
- `phisenapi/`: Core modules including authentication, search, and download.
- `main.py`: Entry point for executing the tool.

---

## Notes
- **Credentials**: Update your username and password in `phisenapi/main.py`. Do **not** share this file publicly.
- **Virtual Environment**: PDM manages a dedicated virtual environment for the project.
- **Faster Setup**: Using `pdm.lock` improves reproducibility and setup speed.

---

## Troubleshooting
- Ensure you're using Python 3.8 or higher.
- Reinstall dependencies using `pdm install`.
- Check logs and error messages for further insights.

---

## License
This project is licensed under the MIT License.