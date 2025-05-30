# SAR Project Documentation

Welcome to the comprehensive documentation for the SAR (Synthetic Aperture Radar) project. This documentation provides detailed information about Sentinel-1 SAR SLC data analysis, including complete attribute references, data schemas, APIs, and usage guidelines.

## Project Overview

This project focuses on the analysis of Sentinel-1 SAR Single Look Complex (SLC) products, providing tools and documentation for:

- **Comprehensive Attribute Analysis**: Based on 5+ years of Sentinel-1 data (2019-2024)
- **26 Core Attributes**: Complete reference for all SAR product metadata
- **Global Coverage**: Analysis spans all geographic regions and operational modes
- **Quality Assessment**: Processing baseline tracking and data validation
- **Temporal Analysis**: Multi-year time series capabilities
- **Spatial Analysis**: Geographic filtering and coordinate handling
- **Orbit Analysis**: Interferometric pair identification and orbit tracking

## Documentation Structure

### 📊 Data Schemas
- [Overview](data-schemas/README.md) - Comprehensive data structure overview
- [Sentinel-1 Attributes](data-schemas/sentinel-1-attributes.md) - Complete attribute reference
- [Product Types](data-schemas/product-types.md) - SAR product type specifications
- [Swath Configurations](data-schemas/swath-configurations.md) - S1-S6 swath details

### 🔧 API Documentation
- [Core APIs](api/README.md) - Complete API reference with examples
- [Search API](api/search-api.md) - Product search functionality
- [Download API](api/download-api.md) - Data download methods
- [Parser API](api/parser-api.md) - Data parsing utilities

### 📖 User Guides
- [Getting Started](user-guides/getting-started.md) - Quick start guide
- [Data Retrieval](user-guides/data-retrieval.md) - How to search and download data
- [Attribute Analysis](user-guides/attribute-analysis.md) - Comprehensive analysis workflows
- [Processing Workflows](user-guides/processing-workflows.md) - Data processing examples

### 📋 Attribute References
- [Comprehensive Reference](attributes/sentinel-1-attributes-reference.md) - Complete attribute documentation
- [Attribute Overview](attributes/README.md) - Summary of all available attributes
- [S1 Swath Attributes](attributes/s1-attributes.md) - S1 specific attributes
- [S2 Swath Attributes](attributes/s2-attributes.md) - S2 specific attributes
- [S3 Swath Attributes](attributes/s3-attributes.md) - S3 specific attributes
- [S4 Swath Attributes](attributes/s4-attributes.md) - S4 specific attributes
- [S5 Swath Attributes](attributes/s5-attributes.md) - S5 specific attributes
- [S6 Swath Attributes](attributes/s6-attributes.md) - S6 specific attributes

## Key Features

### Data Coverage
- **Temporal Span**: 2019-2024 (5+ years of continuous data)
- **Platforms**: Sentinel-1A and Sentinel-1B
- **Geographic Coverage**: Global (all latitudes and longitudes)
- **Operational Modes**: SM, IW, EW, WV
- **Processing Levels**: Focus on L1 SLC products

### Attribute Categories

| Category | Attributes | Description |
|----------|------------|-------------|
| **Temporal** | 5 attributes | Acquisition timing and processing dates |
| **Spatial** | 1 attribute | Geographic coordinates (WKT POLYGON) |
| **Orbit** | 4 attributes | Orbit numbers, direction, and cycles |
| **Platform** | 3 attributes | Satellite and instrument identification |
| **Processing** | 5 attributes | Processing versions and quality |
| **Product** | 5 attributes | Product classification and composition |
| **Configuration** | 3+ attributes | Acquisition modes and settings |

### Quality Indicators
- **Processing Baselines**: Multiple versions tracked (003.40, 003.52, etc.)
- **Processing Centers**: ESA and CGS facilities
- **Data Completeness**: 100% coverage for core attributes
- **Validation**: Schema compliance and integrity checks
1. **Search**: Query Copernicus Data Space for products
2. **Filter**: Apply criteria based on attributes
3. **Download**: Retrieve selected products
4. **Parse**: Extract metadata and data
5. **Analyze**: Process and visualize results

## Version Information

- **Documentation Version**: 1.0.0
- **Last Updated**: 2024
- **Supported Python**: 3.13+
- **Data Source**: Copernicus Data Space Ecosystem

## Support

For questions and support:
- Check the [User Guides](user-guides/) for common tasks
- Review [API Documentation](api/) for technical details
- Examine [Data Schemas](data-schemas/) for format specifications

---

*This documentation is automatically generated and maintained alongside the SAR project codebase.*
