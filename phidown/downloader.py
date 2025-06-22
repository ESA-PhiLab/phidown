from .s5cmd_utils import download


def pull_down(s3path: str,
            outputdir: str,
    verbose: bool = False
    ) -> None:
    """
    Pull down files from S3 using s5cmd with the specified command and configuration.

    Args:
        command (str): The s5cmd command to execute.
        config_file (str): Path to the s5cmd configuration file.
        endpoint_url (str, optional): Custom endpoint URL for S3.
        verbose (bool): If True, print detailed logs.

    Returns:
        str: Output of the s5cmd command.
    """
    if verbose:
        print(f"Pulling down from S3 path: {s3path}")
    
    return download(s3path, output_dir=outputdir) # type: ignore