Changelog
=========

This document tracks all notable changes to Φ-Down.

The format is based on `Keep a Changelog <https://keepachangelog.com/en/1.0.0/>`_,
and this project adheres to `Semantic Versioning <https://semver.org/spec/v2.0.0.html>`_.

[Unreleased]
------------

### Added
- Comprehensive Sphinx documentation with GitHub Pages support
- API reference documentation with autoapi
- User guide with detailed examples
- Interactive tools documentation
- Contributing guidelines

### Changed
- Enhanced project structure for better documentation
- Improved code organization and documentation strings

### Fixed
- Documentation build process
- API reference generation

[0.1.16] - 2024-07-15
---------------------

### Added
- Updated Sentinel-2 reference guide with correct parameters from OpenSearch descriptor
- Comprehensive Sentinel-2 MSI documentation with all product types
- Detailed examples for Level-1C and Level-2A products
- Cloud cover filtering examples and best practices
- Tile-based search documentation with MGRS tile identifiers
- Processing baseline filtering capabilities
- Mission take ID search functionality
- Enhanced Sentinel-3 ocean and land products support
- Sentinel-3 OLCI (Ocean and Land Colour Instrument) documentation
- Sentinel-3 SLSTR (Sea and Land Surface Temperature Radiometer) documentation
- Sentinel-3 SRAL (SAR Radar Altimeter) documentation
- Sentinel-3 MWR (MicroWave Radiometer) documentation
- Comprehensive Sentinel-3 product type reference
- Sentinel-3 instrument-specific search parameters
- Sentinel-3 timeliness and processing level filtering

### Changed
- Corrected Sentinel-2 documentation (was incorrectly showing Sentinel-1 content)
- Enhanced parameter documentation with proper OpenSearch attributes
- Improved search examples with realistic use cases
- Better organization of product types and processing levels
- Updated technical specifications for Sentinel-2 MSI
- Improved Sentinel-3 search parameter organization
- Enhanced multi-mission search capabilities
- Better documentation structure for ocean and land products

### Fixed
- Sentinel-2 reference guide content alignment with actual API parameters
- Parameter mapping between direct parameters and attributes dictionary
- Documentation examples for proper attribute usage
- Product type identifiers and their descriptions
- Sentinel-3 instrument parameter validation
- Cross-mission search consistency
- Product type filtering for ocean and land applications

[0.1.13] - 2024-12-XX
---------------------

### Added
- Interactive polygon selection tools
- Jupyter notebook support with ipyleaflet integration
- Visualization capabilities with folium
- Enhanced search functionality with multiple filters
- S3 download support for faster data access

### Changed
- Improved error handling and logging
- Enhanced credential management
- Better configuration file support
- Optimized search performance

### Fixed
- Authentication issues with Copernicus Data Space
- Download reliability improvements
- Cross-platform compatibility

[0.1.12] - 2024-11-XX
---------------------

### Added
- Cloud cover filtering for optical missions
- Orbit direction filtering for SAR missions
- Enhanced product type validation
- Batch download capabilities

### Changed
- Improved API response handling
- Better error messages and logging
- Enhanced configuration management

### Fixed
- Search parameter validation
- Memory usage optimization
- Network timeout handling

[0.1.11] - 2024-10-XX
---------------------

### Added
- Support for Sentinel-5P atmospheric data
- Enhanced WKT polygon validation
- Progress tracking for downloads
- Configurable timeout settings

### Changed
- Refactored search module for better maintainability
- Improved test coverage
- Enhanced documentation

### Fixed
- Edge cases in date parsing
- Polygon coordinate validation
- Large file download stability

[0.1.10] - 2024-09-XX
---------------------

### Added
- Support for Sentinel-3 ocean and land products
- Advanced filtering capabilities
- Result caching for improved performance
- Custom attribute filtering

### Changed
- Modernized authentication workflow
- Enhanced pandas DataFrame integration
- Improved error handling

### Fixed
- Unicode handling in product names
- Time zone handling for dates
- Memory leaks in large result sets

[0.1.9] - 2024-08-XX
--------------------

### Added
- Comprehensive test suite
- CI/CD pipeline integration
- Code quality checks with flake8
- Type hints throughout the codebase

### Changed
- Refactored codebase for better structure
- Improved documentation strings
- Enhanced logging system

### Fixed
- Dependency version conflicts
- Cross-platform path handling
- SSL certificate verification issues

[0.1.8] - 2024-07-XX
--------------------

### Added
- Support for multiple Sentinel missions
- Flexible search parameter configuration
- Result visualization tools
- Export functionality for search results

### Changed
- Improved API client architecture
- Enhanced configuration management
- Better error reporting

### Fixed
- Authentication token refresh
- Large query result handling
- Network connectivity issues

[0.1.7] - 2024-06-XX
--------------------

### Added
- Initial Sentinel-2 support
- Basic search functionality
- Download capabilities
- Configuration file support

### Changed
- Core architecture improvements
- Enhanced logging system
- Better error handling

### Fixed
- Initial stability issues
- Authentication problems
- Download interruption handling

[0.1.6] - 2024-05-XX
--------------------

### Added
- Sentinel-1 SAR data support
- Product type filtering
- Date range filtering
- Area of interest support

### Changed
- Improved search API design
- Enhanced credential management
- Better documentation

### Fixed
- Search query construction
- Result parsing issues
- Download path handling

[0.1.5] - 2024-04-XX
--------------------

### Added
- Basic Copernicus Data Space integration
- Authentication system
- Simple search interface
- Download functionality

### Changed
- Initial API design
- Core module structure
- Basic configuration system

### Fixed
- Initial implementation bugs
- Authentication workflow
- Basic functionality issues

[0.1.4] - 2024-03-XX
--------------------

### Added
- Project initialization
- Basic package structure
- Core dependencies
- Initial documentation

### Changed
- Project setup and configuration
- Development environment setup
- Basic module architecture

### Fixed
- Package installation issues
- Import problems
- Basic functionality setup

[0.1.3] - 2024-02-XX
--------------------

### Added
- Initial project structure
- Basic utility functions
- Configuration management
- Error handling framework

### Changed
- Core architecture design
- Module organization
- Development workflow

### Fixed
- Package structure issues
- Import path problems
- Basic setup issues

[0.1.2] - 2024-01-XX
--------------------

### Added
- Early prototype functionality
- Basic API design
- Initial testing framework
- Documentation structure

### Changed
- Project architecture
- API design patterns
- Development approach

### Fixed
- Prototype issues
- Basic functionality
- Setup problems

[0.1.1] - 2023-12-XX
--------------------

### Added
- Initial proof of concept
- Basic functionality outline
- Development environment setup
- Project planning

### Changed
- Project scope definition
- Technical approach
- Development strategy

### Fixed
- Initial setup issues
- Basic proof of concept
- Early development problems

[0.1.0] - 2023-11-XX
--------------------

### Added
- Initial project creation
- Basic package structure
- Core concept development
- Project documentation

This is the initial release of Φ-Down, providing basic functionality for searching and downloading Copernicus satellite data.

### Features
- Search Copernicus Data Space catalog
- Download satellite products
- Basic authentication system
- Configuration management
- Error handling and logging

### Supported Missions
- Sentinel-1 (SAR)
- Sentinel-2 (Optical)
- Basic support for other Copernicus missions

### Known Issues
- Limited error handling in some edge cases
- Performance optimization needed for large datasets
- Documentation improvements required

Migration Guide
===============

From 0.1.12 to 0.1.13
---------------------

### New Features
- Interactive tools now available with ``pip install phidown[viz]``
- Enhanced visualization capabilities

### Breaking Changes
- None

### Deprecated
- None

From 0.1.11 to 0.1.12
---------------------

### New Features
- Cloud cover filtering now available for all optical missions
- Orbit direction filtering for SAR missions

### Breaking Changes
- None

### Deprecated
- Old configuration format (still supported but deprecated)

From 0.1.10 to 0.1.11
---------------------

### New Features
- Sentinel-5P support added
- Enhanced polygon validation

### Breaking Changes
- None

### Deprecated
- None

Support Policy
==============

### Supported Versions
- **0.1.13**: Current stable version (full support)
- **0.1.12**: Previous stable version (security updates only)
- **0.1.11**: End of life

### Python Support
- **Python 3.9+**: Fully supported
- **Python 3.8**: End of life
- **Python 3.7**: End of life

### Platform Support
- **macOS**: Fully supported
- **Linux**: Fully supported  
- **Windows**: Fully supported

For older versions or specific support needs, please contact the maintainers or check the GitHub repository.
