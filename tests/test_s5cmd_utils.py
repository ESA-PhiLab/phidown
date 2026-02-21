"""Unit tests for s5cmd helpers with cross-platform command/path coverage."""

from unittest.mock import Mock, patch

import pytest

from phidown.s5cmd_utils import _split_command_args, pull_down, run_s5cmd_with_config


def _write_s5cfg(path):
    path.write_text(
        "\n".join(
            [
                "[default]",
                "aws_access_key_id = 'test-access'",
                "aws_secret_access_key = \"test-secret\"",
                "aws_region = eu-central-1",
                "host_base = eodata.dataspace.copernicus.eu",
                "use_https = true",
            ]
        ),
        encoding="utf-8",
    )


def test_split_command_args_posix_paths_with_spaces():
    cmd = 'cp "s3:/bucket/path with space/*" "/tmp/My Folder/"'
    assert _split_command_args(cmd, platform_name="posix") == [
        "cp",
        "s3:/bucket/path with space/*",
        "/tmp/My Folder/",
    ]


def test_split_command_args_windows_paths_with_spaces():
    cmd = 'cp "s3:/bucket/path/*" "C:\\Users\\User\\My Folder\\"'
    assert _split_command_args(cmd, platform_name="nt") == [
        "cp",
        "s3:/bucket/path/*",
        "C:\\Users\\User\\My Folder\\",
    ]


@patch("phidown.s5cmd_utils.subprocess.Popen")
def test_run_s5cmd_with_config_accepts_command_list(mock_popen, tmp_path):
    cfg = tmp_path / ".s5cfg"
    _write_s5cfg(cfg)

    proc = Mock()
    stdout = Mock()
    stdout.readline.side_effect = ["copy done\n", ""]
    proc.stdout = stdout
    proc.wait.return_value = 0
    mock_popen.return_value = proc

    target_dir = tmp_path / "Folder With Space"
    out = run_s5cmd_with_config(
        ["cp", "s3:/bucket/file", f"{target_dir}/"],
        config_file=str(cfg),
    )

    assert out == "copy done"
    called_cmd = mock_popen.call_args.args[0]
    assert called_cmd[:3] == ["s5cmd", "--endpoint-url", "https://eodata.dataspace.copernicus.eu"]
    assert called_cmd[3:] == ["cp", "s3:/bucket/file", f"{target_dir}/"]

    env = mock_popen.call_args.kwargs["env"]
    assert env["AWS_ACCESS_KEY_ID"] == "test-access"
    assert env["AWS_SECRET_ACCESS_KEY"] == "test-secret"
    assert env["AWS_DEFAULT_REGION"] == "eu-central-1"


def test_run_s5cmd_with_config_rejects_empty_command_sequence(tmp_path):
    cfg = tmp_path / ".s5cfg"
    _write_s5cfg(cfg)
    with pytest.raises(ValueError, match="Command cannot be empty"):
        run_s5cmd_with_config([], config_file=str(cfg))


@patch("phidown.s5cmd_utils.run_s5cmd_with_config")
def test_pull_down_passes_list_command_and_preserves_spaces(mock_run, tmp_path):
    cfg = tmp_path / ".s5cfg"
    _write_s5cfg(cfg)

    output_dir = tmp_path / "Output Folder"
    s3_path = (
        "/eodata/Sentinel-1/SAR/IW_RAW__0S/2024/05/03/"
        "S1A_IW_RAW__0SDV_20240503T031926_20240503T031942_053701_0685FB_E003.SAFE"
    )

    ok = pull_down(
        s3_path=s3_path,
        output_dir=str(output_dir),
        config_file=str(cfg),
        show_progress=False,
        download_all=True,
    )

    assert ok is True
    kwargs = mock_run.call_args.kwargs
    assert kwargs["command"] == [
        "cp",
        f"s3:/{s3_path}/*",
        (
            f"{output_dir}/"
            "S1A_IW_RAW__0SDV_20240503T031926_20240503T031942_053701_0685FB_E003.SAFE/"
        ),
    ]
