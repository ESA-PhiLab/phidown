---
title: "phidown: Python tools for reproducible access to Copernicus Data Space Ecosystem data"
tags:
  - Python
  - earth observation
  - remote sensing
  - Copernicus
  - Sentinel-1
authors:
  - name: Roberto Del Prete
    affiliation: 1
affiliations:
  - index: 1
    name: Phi-lab, European Space Agency, Frascati, Italy
date: 19 March 2026
bibliography: paper.bib
---

# Summary

`phidown` is an open-source Python package and command-line interface for
searching and downloading Earth observation data from the Copernicus Data Space
Ecosystem (CDSE) [@cdse]. It targets researchers and engineers who need a
lightweight interface to official Copernicus data services without building
custom clients for authentication, catalogue queries, and object-store
downloads.

The package supports multi-mission catalogue search, product download, and
Sentinel-1 burst-oriented workflows through a consistent Python API and terminal
commands. Search results are returned as `pandas.DataFrame` objects, which
makes the outputs easy to inspect, filter, and pass into downstream analysis
notebooks or automated pipelines. The project is distributed under the Apache
License 2.0, published on PyPI, and documented in a public documentation site
[@phidown_docs].

# Statement of need

Open access to Copernicus data enables research in environmental monitoring,
remote sensing, climate analytics, and Earth observation machine learning.
However, turning that access into a reproducible workflow is still operationally
burdensome. CDSE exposes catalogue and download capabilities through web APIs
and S3-compatible storage [@cdse], but day-to-day research usage still requires
users to manage credentials, compose OData filters, handle pagination, switch
between search and transfer endpoints, and adapt those steps to mission-specific
metadata.

`phidown` is designed for remote sensing researchers, research software
engineers, and applied data scientists who need a smaller and more workflow-led
interface than a full cloud processing platform. The package reduces the
friction between "find the right product" and "get the data into analysis code"
by exposing a unified set of Python and CLI entry points for search, direct
download, and burst selection. This is especially useful when assembling
reproducible data-ingestion pipelines for Sentinel-1, Sentinel-2, Sentinel-3,
and Sentinel-5P products.

The most distinctive need addressed by `phidown` is access to Sentinel-1 burst
products generated on demand by CDSE. Burst-level access matters for InSAR time
series preparation, local-area monitoring, and machine learning dataset curation
because it avoids repeatedly downloading complete SLC scenes when only a subset
of bursts is relevant. `phidown` exposes this capability through query
parameters, workflow helpers, and diagnostics that fit directly into Python
analysis environments.

# State of the field

Several Python tools already support parts of the Copernicus access workflow,
but they do not occupy the same design space as `phidown`. `sentinelsat` became
widely used for querying and downloading Sentinel products from the former
Copernicus Open Access Hub, but the upstream project now documents that it is
not functional for CDSE downloads and the repository was archived in October
2025 [@sentinelsat_repo]. `sentinelhub-py` is the official Python interface for
Sentinel Hub services, which makes it useful for a different access model based
on Sentinel Hub infrastructure rather than a focused wrapper around the official
CDSE catalogue and download endpoints [@sentinelhubpy].

This context explains the "build vs. contribute" decision for `phidown`.
Adapting `sentinelsat` to CDSE would have required reworking a project centered
on the legacy DHuS ecosystem and now archived upstream. Extending
`sentinelhub-py` would not have matched that project's primary focus on Sentinel
Hub services and processing APIs. `phidown` instead focuses narrowly on the
official CDSE search and transfer path: catalogue queries, CDSE-compatible
download operations, and Sentinel-1 burst workflows. That narrower scope is the
main scholarly contribution of the package because it turns an operational data
access problem into a reusable research tool for reproducible ingestion and
selection of Copernicus products.

# Software design

The package is organized around a small number of composable layers. The core
search layer is centered on `CopernicusDataSearcher`, which validates query
parameters, translates high-level filters into CDSE-compatible requests, handles
pagination and retry behavior, and returns normalized tabular results for
inspection and downstream processing. This keeps the research-facing interface
compact while isolating API-specific request construction and error handling in a
single place.

The download layer separates authentication and transfer concerns from the query
logic. `phidown` supports a fast path that shells out to `s5cmd` for bulk S3
transfers and a safe path that performs resumable native downloads for more
fragile environments. That split is important in practice: high-throughput data
staging and robust recovery from interrupted transfers are both common research
requirements, but they trade off simplicity, speed, and failure recovery
differently. The CLI and Python API expose the same conceptual download modes so
users can move between exploratory and automated workflows without learning two
different interfaces.

Sentinel-1 burst workflows are implemented as a higher-level orchestration layer
on top of the search interface. The burst workflow module builds configuration
objects, recommends orbit settings, retrieves burst products for an area of
interest, computes summary statistics, and exports validation artefacts such as
CSV tables and JSON reports. Optional modules for visualization, AIS utilities,
and interactive polygon tools are imported lazily so the base installation stays
lightweight for users who only need search and download features. This structure
keeps the default package install small while still allowing more advanced,
domain-specific workflows in the same project.

# Research impact statement

`phidown` currently demonstrates credible near-term research significance with
several concrete reuse signals. The project has a citable Zenodo release
[@phidown_zenodo], a public PyPI distribution [@phidown_pypi], public
documentation [@phidown_docs], and automated cross-platform tests in the public
repository. Those features make the software directly installable, inspectable,
and verifiable by external researchers rather than limiting it to an internal
lab script.

The package is also documented outside the repository itself. An ESA Phi-lab
project page describes `phidown` as research software for simplifying access to
Copernicus Data Space data [@phidown_cin], and external Earth-observation
community outlets have highlighted the package as a practical way to access
Copernicus data programmatically [@phidown_satellite_image_dl;
@phidown_spectral_reflectance]. These are modest but concrete indicators that
the software has moved beyond a private prototype and is already visible to the
community that would reuse it.

Within ESA Phi-lab, `phidown` has been used in workflows that require repeated
access to CDSE products, including Sentinel-1 burst selection and broader Earth
observation data ingestion for downstream analysis. The repository also contains
notebooks, workflow helpers, and validation outputs that document how the burst
search and diagnostics are applied in practice. Together, these materials show
that the package already supports reproducible research operations and provides
the ingredients needed for near-term reuse by other groups facing the same CDSE
access bottlenecks.

The package's strongest impact signal remains its support for Sentinel-1 burst
access through a stable Python and CLI interface. Burst-level workflows are
increasingly important for InSAR-oriented studies and targeted dataset creation
because they reduce unnecessary transfers of full scenes and make area-specific
time series assembly easier to automate. By packaging these capabilities behind
a documented, tested interface, `phidown` lowers the cost of integrating
official CDSE data access into research pipelines.

# AI usage disclosure

Generative AI tools were used to assist with drafting and editing portions of
the JOSS submission materials, including this manuscript. Human authors reviewed
and edited all AI-assisted text, verified the technical claims and citations,
and retained responsibility for the software design decisions, code behavior,
and final wording of the submission. This disclosure applies to the preparation
of the submission materials; no AI-generated content was accepted without human
validation.

# Acknowledgements

Development of `phidown` was supported by the European Space Agency (ESA)
Phi-lab as part of its work on AI-ready cloud infrastructures and on-board
intelligence for Earth observation. The author thanks the Copernicus Data Space
team for technical guidance and the project contributors who helped test and
refine the package.

# References
