<div align="center">

# 📦 **Φ**-Down: Copernicus Data Management Tool

</div>

![Phi-Down Logo](./assets/phidown_logo.png)

#### This repository provides tools for managing Sentinel data using AWS services and dataset tools. It includes functionality for authentication, product search, and downloading Earth Observation (EO) products.

> **⚠️ Search Optimization Tips⚠️**  
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

The following collections are currently available:

<details>
<summary><strong>Copernicus Sentinel Mission</strong></summary>

- SENTINEL-1
- SENTINEL-2
- SENTINEL-3
- SENTINEL-5P
- SENTINEL-6
- SENTINEL-1-RTC (Sentinel-1 Radiometric Terrain Corrected)

</details>

<details>
<summary><strong>Complementary data</strong></summary>

- GLOBAL-MOSAICS (Sentinel-1 and Sentinel-2 Global Mosaics)
- SMOS (Soil Moisture and Ocean Salinity)
- ENVISAT (ENVISAT- Medium Resolution Imaging Spectrometer - MERIS)
- LANDSAT-5
- LANDSAT-7
- LANDSAT-8
- COP-DEM (Copernicus DEM)
- TERRAAQUA (Terra MODIS and Aqua MODIS)
- S2GLC (S2GLC 2017)

</details>

<details>
<summary><strong>Copernicus Contributing Missions (CCM)</strong></summary>
<!-- Add CCM collections here if available -->
</details>

---

## Prerequisites
- Python 3.8 or higher

---

## Installation

### Step 1: Install PDM
We gonna use [PDM](https://pdm.fming.dev/) (Python Dependency Manager) to simplify our life. 
If you don't already have PDM installed, install it via pip:
```bash
pip install pdm
```

### Step 2: Install Dependencies Using PDM
Use the `pdm.lock` file to install exact versions of dependencies:
```bash
pdm add git+https://github.com/sirbastiano/phidown.git
pdm install
```

### Alternative: Build from source
If you prefer using pip, you can install the dependencies directly:
```bash
git clone https://github.com/sirbastiano/phidown.git & cd phidown
pip install .
```

This will install the package and its dependencies as defined in the `pyproject.toml` file.

---

## Usage

### Step 4: Configure Credentials

To authenticate with the Copernicus Data Space Ecosystem, you need to create a `secret.yml` file containing your credentials. Follow these steps:

1. Create a file named `secret.yml` in the root directory of the project.
2. Add the following content to the file, replacing `your_username` and `your_password` with your actual credentials:

   ```yaml
   # filepath: ./phidown/secret.yml
   copernicus:
     username: your_username
     password: your_password
   ```

3. Save the file.

### Alternative: Pass Credentials at Execution

Instead of using a `secret.yml` file, you can pass your credentials directly when running the script. Use the following command:

```bash
pdm run python phidown/downloader.py --username your_username --password your_password --eo_product_name <eo_product_name>
```

Replace `your_username` and `your_password` with your actual credentials.
Replace `eo_product_name` with your actual product name you want to download.

The script will:
1. Authenticate with the Copernicus Data Space Ecosystem.
2. Search for Sentinel products within the specified AOI and date range.
3. Download the first matching product using S3.


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
This project is licensed under the CC by 2.0 License.