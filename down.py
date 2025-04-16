import subprocess
import sys

def run_downloader(eo_product_name, username=None, password=None):
    """
    Run downloader.py as a module using subprocess.
    """
    command = [sys.executable, "-m", "phidown.downloader", "-eo_product_name", eo_product_name]
    
    if username:
        command.extend(["-u", username])
    if password:
        command.extend(["-p", password])
    
    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error occurred while running downloader: {e}")
        sys.exit(1)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run downloader.py as a module.")
    parser.add_argument("-eo_product_name", type=str, required=True, help="Name of the EO product to download")
    parser.add_argument("-u", "--username", type=str, help="Username for authentication (optional)")
    parser.add_argument("-p", "--password", type=str, help="Password for authentication (optional)")
    args = parser.parse_args()

    run_downloader(args.eo_product_name, args.username, args.password)
