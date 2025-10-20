---
title: "phidown: A Python library for simplified access to Copernicus Earth Observation data"
authors:
  - name: Roberto Del Prete
    affiliation: 1
affiliations:
  - index: 1
    name: Φ-lab, European Space Agency, Frascati, Italy
date: 18 October 2025
bibliography: paper.bib
---

# Summary

*phidown* is an open-source Python package developed at the European Space Agency’s Φ-lab to simplify and accelerate access to the Copernicus Data Space Ecosystem (CDSE).  
It provides a high-level interface for searching, filtering, and downloading Earth-observation (EO) products — including advanced functionality for Sentinel-1 burst-level access — while abstracting away the complexity of APIs, authentication, and data-transfer protocols.

Modern EO missions such as Sentinel-1, Sentinel-2, and Sentinel-3 generate petabytes of data each year. Accessing this information typically requires familiarity with REST/OData queries, token-based authentication, and mission-specific metadata. *phidown* addresses these challenges through a lightweight, Pythonic interface that integrates natively with scientific workflows.  
Search results are returned as `pandas.DataFrame` objects, enabling seamless data manipulation, visualization, and export within Jupyter environments.  

By combining flexibility and performance, *phidown* empowers researchers and developers to focus on higher-level analysis — from land-cover mapping to interferometric SAR (InSAR) time-series generation — instead of manual data handling.  
It is distributed under the GNU Lesser General Public License v3.0 and maintained by ESA Φ-lab with public documentation and community support.

# Statement of need

Efficient access to satellite data is a fundamental enabler for environmental monitoring, climate modeling, and AI-driven Earth-observation research.  
While the Copernicus Data Space Ecosystem offers a unified platform for accessing Sentinel mission data, interacting with its APIs remains non-trivial for most users.  
Developers must manage OAuth tokens, craft complex OData queries, and handle asynchronous downloads — a workflow prone to errors and reproducibility issues.

Existing libraries such as `sentinelsat` or `sentinelhub-py` provide partial solutions but are often mission-specific or tied to proprietary infrastructures.  
*phidown* fills this gap by providing a mission-agnostic, open-source Python interface that supports multiple Sentinel collections (S1, S2, S3, S5P) and directly interacts with CDSE endpoints.  

Its most distinctive feature is the **Sentinel-1 burst-mode API**, which enables users to query and retrieve individual IW or EW bursts via their unique `burst_id`.  
These burst products are generated on-demand by CDSE, allowing fine-grained spatial and temporal control over SAR datasets — a capability crucial for InSAR applications, interferogram synthesis, and machine-learning dataset generation.  

By democratizing access to raw and pre-processed data, *phidown* contributes to reproducible, scalable EO research.  
The software has already been adopted within ESA Φ-lab projects related to onboard AI (e.g., Φ-Sat, Syrious EDGE) and Copernicus downstream innovation activities, enabling reproducible pipelines for large-scale SAR data ingestion and AI model training.

# Features

Written entirely in Python (≥ 3.9), *phidown* leverages the modern open-source data-science ecosystem.  
Key features include:

- **Unified API access** to the CDSE OData interface, supporting multi-mission filtering by area of interest, acquisition time, orbit direction, polarization, and cloud cover.  
- **High-performance downloads** using the S5 protocol via `s5cmd`, with automatic fallbacks to S3.  
- **Sentinel-1 burst-mode querying**, allowing selection and retrieval of single bursts by `burst_id`.  
- **Automatic credential management**, supporting both environment variables and configuration files.  
- **Pythonic data handling**, returning search results as `pandas.DataFrame` objects ready for further analysis.  
- **Cross-platform compatibility**, with tested support for Linux, macOS, and Windows.  
- **Comprehensive documentation and examples**, including Jupyter notebooks demonstrating typical use cases.

The package design emphasizes modularity: each functional block (authentication, search, download) can be extended independently, facilitating integration with cloud pipelines, schedulers, or custom processing frameworks.

# Acknowledgements

Development of *phidown* was supported by the European Space Agency (ESA) Φ-lab as part of its research in AI-ready cloud infrastructures and on-board intelligence for Earth observation.  
The author thanks the Copernicus Data Space team for technical guidance and all contributors who provided feedback during testing and release cycles.

# References

Del Prete, R. (2025). *phidown: A Python library for simplified access to Copernicus Data Space Ecosystem data*. Zenodo. https://doi.org/10.5281/zenodo.15332053  

European Space Agency Φ-lab. (2025). *phidown documentation*. https://esa-philab.github.io/phidown/  

Del Prete, R. (2024). *Φ-Down: A Python library to simplify access to Copernicus Data Space Ecosystem EO data.* ESA Φ-lab CIN Visiting Researcher Project.  
https://cin.philab.esa.int/databases/projects/down-a-python-library-to-simplify-access-eo-data-from-the-copernicus-data-space-ecosystem  

Satellite Image Deep Learning (2025). *PhiDown: Fast, Simple Access to Copernicus Data.*  
https://www.satellite-image-deep-learning.com/p/phidown-fast-simple-access-to-copernicus  

Spectral Reflectance Newsletter #122
https://www.spectralreflectance.space/p/spectral-reflectance-newsletter-122