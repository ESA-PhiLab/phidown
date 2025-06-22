#!/usr/bin/env python3
"""Entry point for running phidown.downloader as a module.

This prevents the RuntimeWarning about module execution conflicts.
"""

if __name__ == '__main__':
    # Import and run the downloader directly
    from .downloader_boto3 import main
    main()
