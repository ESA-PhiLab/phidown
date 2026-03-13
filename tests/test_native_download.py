import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from phidown.native_download import download_s3_resumable


class _FakeBody:
    def __init__(self, chunks):
        self._chunks = chunks

    def iter_chunks(self, chunk_size=None):
        for chunk in self._chunks:
            yield chunk


class _FakeClient:
    def __init__(self, *, head_map=None, list_pages=None, get_responses=None):
        self.head_map = head_map or {}
        self.list_pages = list_pages or []
        self.get_responses = list(get_responses or [])
        self.get_calls = []

    def head_object(self, Bucket, Key):
        return self.head_map[(Bucket, Key)]

    def get_paginator(self, name):
        assert name == "list_objects_v2"

        class _Paginator:
            def __init__(self, pages):
                self.pages = pages

            def paginate(self, **kwargs):
                return list(self.pages)

        return _Paginator(self.list_pages)

    def get_object(self, **kwargs):
        self.get_calls.append(kwargs)
        return self.get_responses.pop(0)


def test_download_s3_resumable_resumes_single_object_with_range(tmp_path, monkeypatch):
    output_dir = tmp_path / "out"
    final_path = output_dir / "file.bin"
    temp_path = final_path.with_suffix(".bin.part")
    temp_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path.write_bytes(b"head")

    client = _FakeClient(
        head_map={
            ("eodata", "Sentinel-1/SAR/file.bin"): {
                "ContentLength": 8,
                "ETag": '"etag-1"',
            }
        },
        get_responses=[
            {
                "ResponseMetadata": {"HTTPStatusCode": 206},
                "Body": _FakeBody([b"tail"]),
            }
        ],
    )

    monkeypatch.setattr("phidown.native_download.ensure_s5cmd_config", lambda *args, **kwargs: None)
    monkeypatch.setattr("phidown.native_download._build_s3_client", lambda *args, **kwargs: client)

    result = download_s3_resumable(
        s3_path="/eodata/Sentinel-1/SAR/file.bin",
        output_dir=str(output_dir),
        config_file=str(tmp_path / ".s5cfg"),
        download_all=False,
    )

    assert result.status == "downloaded"
    assert final_path.read_bytes() == b"headtail"
    assert not temp_path.exists()
    assert client.get_calls[0]["Range"] == "bytes=4-"


def test_download_s3_resumable_restarts_when_range_not_honored(tmp_path, monkeypatch):
    output_dir = tmp_path / "out"
    final_path = output_dir / "file.bin"
    temp_path = final_path.with_suffix(".bin.part")
    temp_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path.write_bytes(b"old")

    client = _FakeClient(
        head_map={
            ("eodata", "Sentinel-1/SAR/file.bin"): {
                "ContentLength": 8,
                "ETag": '"etag-1"',
            }
        },
        get_responses=[
            {
                "ResponseMetadata": {"HTTPStatusCode": 200},
                "Body": _FakeBody([b"ignored"]),
            },
            {
                "ResponseMetadata": {"HTTPStatusCode": 200},
                "Body": _FakeBody([b"freshdat"]),
            },
        ],
    )

    monkeypatch.setattr("phidown.native_download.ensure_s5cmd_config", lambda *args, **kwargs: None)
    monkeypatch.setattr("phidown.native_download._build_s3_client", lambda *args, **kwargs: client)

    result = download_s3_resumable(
        s3_path="/eodata/Sentinel-1/SAR/file.bin",
        output_dir=str(output_dir),
        config_file=str(tmp_path / ".s5cfg"),
        download_all=False,
    )

    assert result.status == "downloaded"
    assert final_path.read_bytes() == b"freshdat"
    assert len(client.get_calls) == 2
    assert client.get_calls[0]["Range"] == "bytes=3-"
    assert "Range" not in client.get_calls[1]


def test_single_object_download_uses_requested_output_dir_basename(tmp_path, monkeypatch):
    output_dir = tmp_path / "out"
    key = "Sentinel-1/A/path/shared.bin"
    client = _FakeClient(
        head_map={
            ("eodata", key): {"ContentLength": 3, "ETag": '"a"'},
        },
        get_responses=[
            {"ResponseMetadata": {"HTTPStatusCode": 200}, "Body": _FakeBody([b"one"])},
        ],
    )

    monkeypatch.setattr("phidown.native_download.ensure_s5cmd_config", lambda *args, **kwargs: None)
    monkeypatch.setattr("phidown.native_download._build_s3_client", lambda *args, **kwargs: client)

    result = download_s3_resumable(
        s3_path=f"/eodata/{key}",
        output_dir=str(output_dir),
        config_file=str(tmp_path / ".s5cfg"),
        download_all=False,
        persist_state=False,
    )

    expected_path = output_dir / "shared.bin"
    assert result.output_path == str(expected_path)
    assert expected_path.read_bytes() == b"one"


def test_single_object_download_redownloads_same_basename_without_state(tmp_path, monkeypatch):
    output_dir = tmp_path / "out"
    key_a = "Sentinel-1/A/path/shared.bin"
    key_b = "Sentinel-2/B/path/shared.bin"
    client = _FakeClient(
        head_map={
            ("eodata", key_a): {"ContentLength": 3, "ETag": '"a"'},
            ("eodata", key_b): {"ContentLength": 3, "ETag": '"b"'},
        },
        get_responses=[
            {"ResponseMetadata": {"HTTPStatusCode": 200}, "Body": _FakeBody([b"one"])},
            {"ResponseMetadata": {"HTTPStatusCode": 200}, "Body": _FakeBody([b"two"])},
        ],
    )

    monkeypatch.setattr("phidown.native_download.ensure_s5cmd_config", lambda *args, **kwargs: None)
    monkeypatch.setattr("phidown.native_download._build_s3_client", lambda *args, **kwargs: client)

    first = download_s3_resumable(
        s3_path=f"/eodata/{key_a}",
        output_dir=str(output_dir),
        config_file=str(tmp_path / ".s5cfg"),
        download_all=False,
        persist_state=False,
    )
    second = download_s3_resumable(
        s3_path=f"/eodata/{key_b}",
        output_dir=str(output_dir),
        config_file=str(tmp_path / ".s5cfg"),
        download_all=False,
        persist_state=False,
    )

    assert first.output_path == second.output_path == str(output_dir / "shared.bin")
    assert os.path.exists(second.output_path)
    assert (output_dir / "shared.bin").read_bytes() == b"two"
    assert len(client.get_calls) == 2
