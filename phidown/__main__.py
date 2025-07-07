#!/usr/bin/env python3
"""Entry point for running phidown as a module.

This provides basic help and information about the phidown package.
"""

def main():
    """Main entry point for the phidown package."""
    print("Φ-Down - Copernicus Data Downloader")
    print("===================================")
    print()
    print("Usage:")
    print("  python -m phidown --help")
    print()
    print("For interactive usage, use the Python API:")
    print("  from phidown import CopernicusDataSearcher")
    print("  from phidown.downloader import pull_down")
    print()
    print("Documentation: https://esa-philab.github.io/phidown")
    print()
    print("Note: Make sure to set up your .s5cfg file with S3 credentials.")
    print("See the documentation for details.")

if __name__ == '__main__':
    main()
