#!/bin/bash
# source down.sh > logfile 2>&1

# Download product with improved error handling
echo "Downloading..."
python -m phidown -eo_product_name S1A_S3_SLC__1SDH_20240430T213606_20240430T213631_053668_0684A3_FCED.SAFE

# Check exit status and provide helpful feedback
exit_status=$?
if [ $exit_status -eq 0 ]; then
    echo "Download completed successfully!"
else
    echo "Download failed with exit code: $exit_status"
    echo "Common causes:"
    echo "  - 403 Forbidden: Check your AWS S3 credentials and permissions"
    echo "  - Network connectivity issues"
    echo "  - Invalid product name"
    echo "Check the logs above for detailed error information."
    exit $exit_status
fi