import subprocess
import os
from typing import Optional, List
import configparser
import logging
import shlex
import time
import threading
from tqdm import tqdm

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_s5cmd_with_config(
    command: str,
    config_file: str = '.s5cfg',
    endpoint_url: Optional[str] = None,
    verbose: bool = False,
) -> str:
    """Run s5cmd command with configuration file.

    This function executes s5cmd commands using credentials from a configuration
    file and handles endpoint URL configuration for the Copernicus Data Space.

    Args:
        command: The s5cmd command to execute (without 's5cmd' prefix)
        config_file: Path to s5cmd configuration file (default: '.s5cfg')
        endpoint_url: Optional endpoint URL override
        verbose: Whether to print command being executed

    Returns:
        str: Command output as string

    Raises:
        subprocess.CalledProcessError: If command fails
        FileNotFoundError: If config file is not found

    Example:
        >>> output = run_s5cmd_with_config('ls s3://eodata/Sentinel-1/')
    """
    assert command.strip(), 'Command cannot be empty'

    # Parse the config file
    config = configparser.ConfigParser()
    if not os.path.exists(config_file):
        raise FileNotFoundError(f'Configuration file {config_file} not found')

    config.read(config_file)

    # Set environment variables from config
    env = os.environ.copy()
    if 'default' in config:
        default_section = config['default']
        env['AWS_ACCESS_KEY_ID'] = default_section.get('aws_access_key_id', '').strip("'\"")
        env['AWS_SECRET_ACCESS_KEY'] = default_section.get('aws_secret_access_key', '').strip("'\"")
        env['AWS_DEFAULT_REGION'] = default_section.get('aws_region', 'us-east-1').strip("'\"")

    # Build command
    cmd_parts = ['s5cmd']

    # Add endpoint URL
    if endpoint_url:
        cmd_parts.extend(['--endpoint-url', endpoint_url])
    elif 'default' in config and 'host_base' in config['default']:
        host_base = config['default']['host_base'].strip("'\"")
        use_https = config['default'].get('use_https', 'true').strip("'\"").lower() == 'true'
        protocol = 'https' if use_https else 'http'
        cmd_parts.extend(['--endpoint-url', f'{protocol}://{host_base}'])

    # Parse command properly using shlex to handle quotes and wildcards
    command_args = shlex.split(command)
    cmd_parts.extend(command_args)

    if verbose:
        logger.info(f'Running command: {" ".join(cmd_parts)}')

    # Run the command and stream output so the user can see progress live
    # We collect stdout lines and also log them in real time.
    process = subprocess.Popen(
        cmd_parts,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env
    )

    stdout_lines: List[str] = []
    try:
        assert process.stdout is not None
        for line in iter(process.stdout.readline, ''):
            # strip trailing newlines but preserve message
            text_line = line.rstrip('\n')
            if text_line:
                if verbose:
                    logger.info(text_line)
                stdout_lines.append(text_line)

        returncode = process.wait()
        if returncode != 0:
            # Join collected output for better error context
            combined = "\n".join(stdout_lines)
            if verbose:
                logger.error(f'Command exited with non-zero status {returncode}. '
                             f'Output:\n{combined}')
            raise subprocess.CalledProcessError(returncode, cmd_parts, output=combined)

        return "\n".join(stdout_lines)
    except Exception:
        # If something goes wrong, ensure process is terminated
        try:
            process.kill()
        except Exception:
            pass
        raise


def get_directory_size(directory: str) -> int:
    """Calculate total size of all files in a directory recursively.
    
    Args:
        directory: Path to the directory
        
    Returns:
        int: Total size in bytes
    """
    total_size = 0
    try:
        for dirpath, dirnames, filenames in os.walk(directory):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                if os.path.exists(filepath):
                    total_size += os.path.getsize(filepath)
    except Exception as e:
        logger.warning(f'Error calculating directory size: {e}')
    return total_size


def pull_down(
    s3_path: str,
    output_dir: str = '.',
    config_file: str = '.s5cfg',
    endpoint_url: str = 'https://eodata.dataspace.copernicus.eu',
    download_all: bool = True,
    reset: bool = False,
    total_size: Optional[int] = None,
    show_progress: bool = True
) -> bool:
    """Download Sentinel-1 SAFE directory from Copernicus Data Space.

    This function downloads either individual files or entire SAFE directories
    from the Copernicus Data Space Ecosystem using the optimized s5cmd tool.
    Optionally displays a progress bar based on downloaded file size.

    Args:
        s3_path: S3 path to the Sentinel-1 data (should start with /eodata/)
        output_dir: Local output directory for downloaded files
        config_file: Path to s5cmd configuration file
        endpoint_url: Copernicus Data Space endpoint URL
        download_all: If True, downloads entire directory with wildcard pattern
        reset: If True, prompts for new AWS credentials and resets config file
        total_size: Expected total size in bytes (for progress bar)
        show_progress: If True and total_size provided, shows tqdm progress bar

    Returns:
        bool: True if download was successful

    Raises:
        subprocess.CalledProcessError: If download fails
        ValueError: If s3_path format is invalid

    Example:
        >>> # Download entire SAFE directory with progress bar
        >>> output = pull_down(
        ...     '/eodata/Sentinel-1/SAR/IW_RAW__0S/2024/05/03/'
        ...     'S1A_IW_RAW__0SDV_20240503T031926_20240503T031942_053701_0685FB_E003.SAFE',
        ...     output_dir='/path/to/data',
        ...     total_size=1073741824,  # 1 GB
        ...     show_progress=True
        ... )

    Notes:
        - s5cmd is executed as a subprocess and its stdout/stderr are streamed
          in real time to the logger. This means when `pull_down` runs you
          will see file copy progress and status messages as they happen.
        - Ensure `s5cmd` is installed and available on PATH. There is no
          additional environment variable required to enable streaming; it's
          handled by this function.
        - Progress bar monitors actual disk usage and updates in real-time.
    """
    assert s3_path, 'S3 path cannot be empty'
    assert output_dir, 'Output directory arg cannot be empty'
    assert os.path.isabs(output_dir), 'Output directory must be an absolute path'
    # validate config file:
    # try to create one config file if it does not exist
    if not os.path.exists(config_file) or reset:
        access_key = input('Enter Access Key ID: ').strip()
        secret_key = input('Enter Secret Access Key: ').strip()

        config_content = f"""[default]
                        aws_access_key_id = {access_key}
                        aws_secret_access_key = {secret_key}
                        aws_region = eu-central-1
                        host_base = eodata.dataspace.copernicus.eu
                        host_bucket = eodata.dataspace.copernicus.eu
                        use_https = true
                        check_ssl_certificate = true
                        """

        with open(config_file, 'w') as f:
            f.write(config_content)

        logger.info(f'Created configuration file: {config_file}')

    assert os.path.exists(config_file), f'Configuration file {config_file} still not found.'
    assert s3_path.startswith('/eodata/'), f'S3 path must start with /eodata/, got: {s3_path}'

    # Create output directory with SAFE name
    safe_name = os.path.basename(s3_path.rstrip('/'))
    full_output_dir = os.path.join(output_dir, safe_name)
    os.makedirs(full_output_dir, exist_ok=True)

    # Construct proper S3 URL
    if download_all and not s3_path.endswith('/*'):
        # For directory download, add wildcard
        s3_url = f's3:/{s3_path}/*'
    else:
        s3_url = f's3:/{s3_path}'

    # Build the cp command - don't use quotes in the command string
    # The subprocess will handle arguments properly
    command = f'cp {s3_url} {full_output_dir}/'

    if show_progress and total_size and total_size > 0:
        # Suppress info logging when progress bar is shown
        pass
    else:
        logger.info(f'Downloading from: {s3_url}')
        logger.info(f'Output directory: {full_output_dir}')
    
    # If progress bar is enabled and total_size is provided
    if show_progress and total_size and total_size > 0:
        # Get initial size
        initial_size = get_directory_size(full_output_dir)
        
        # Create progress bar
        pbar = tqdm(
            total=total_size,
            initial=initial_size,
            unit='B',
            unit_scale=True,
            unit_divisor=1024,
            desc='Downloading'
        )
        
        # Flag to stop monitoring thread
        stop_monitoring = threading.Event()
        
        def monitor_progress():
            """Monitor download progress by checking disk usage."""
            last_size = initial_size
            while not stop_monitoring.is_set():
                time.sleep(0.5)  # Update every 0.5 seconds
                current_size = get_directory_size(full_output_dir)
                delta = current_size - last_size
                if delta > 0:
                    pbar.update(delta)
                    last_size = current_size
        
        # Start monitoring thread
        monitor_thread = threading.Thread(target=monitor_progress, daemon=True)
        monitor_thread.start()
        
        try:
            run_s5cmd_with_config(
                command=command,
                config_file=config_file,
                endpoint_url=endpoint_url,
                verbose=False  # Reduce logging noise when using progress bar
            )
        finally:
            # Stop monitoring and ensure final update
            stop_monitoring.set()
            monitor_thread.join(timeout=2)
            
            # Final size check
            final_size = get_directory_size(full_output_dir)
            remaining = final_size - pbar.n
            if remaining > 0:
                pbar.update(remaining)
            
            pbar.close()
    else:
        # No progress bar - use original implementation
        run_s5cmd_with_config(
            command=command,
            config_file=config_file,
            endpoint_url=endpoint_url
        )
    
    return True
