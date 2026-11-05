"""Tests for download state persistence and helpers."""

import os
from datetime import datetime, timezone
from unittest.mock import patch

import pandas as pd

from phidown.download_state import (
    DownloadStateStore,
    can_skip_download,
    default_state_file,
    is_non_empty_file,
    is_product_complete,
    is_single_file_s3_path,
    utc_now_iso,
)


def test_default_state_file_path(tmp_path):
    out = default_state_file(str(tmp_path))
    # Use os.path.join for platform-independent path checking
    expected_suffix = os.path.join('.phidown', 'download_state.json')
    assert out.endswith(expected_suffix)
    # Verify the .phidown directory is created
    assert (tmp_path / '.phidown').is_dir()


def test_utc_now_iso_returns_aware_utc_timestamp():
    ts = utc_now_iso()
    parsed = datetime.fromisoformat(ts)

    assert parsed.tzinfo is not None
    assert parsed.utcoffset() == timezone.utc.utcoffset(parsed)


def test_state_store_persists_records(tmp_path):
    state_path = tmp_path / 'state.json'
    store = DownloadStateStore(str(state_path))

    store.mark('item-1', 'in_progress', attempts=1, output_path='/tmp/item')
    store.mark('item-1', 'success', attempts=1, output_path='/tmp/item')

    reloaded = DownloadStateStore(str(state_path))
    item = reloaded.get('item-1')
    assert item is not None
    assert item['status'] == 'success'
    assert item['attempts'] == 1


def test_state_store_recovers_from_invalid_json(tmp_path):
    state_path = tmp_path / 'state.json'
    state_path.write_text('{not valid json', encoding='utf-8')

    store = DownloadStateStore(str(state_path))

    assert store.get('missing') is None
    store.set('item-1', {'status': 'success'})
    assert store.get('item-1') == {'status': 'success'}


def test_mark_success_preserves_attempts_and_output_but_clears_error(tmp_path):
    state_path = tmp_path / 'state.json'
    store = DownloadStateStore(str(state_path))

    store.mark('item-1', 'failed', attempts=2, output_path='/tmp/out', error='boom')
    store.mark('item-1', 'success')

    record = store.get('item-1')
    assert record is not None
    assert record['status'] == 'success'
    assert record['attempts'] == 2
    assert record['output_path'] == '/tmp/out'
    assert 'error' not in record


def test_product_and_file_completion_helpers(tmp_path):
    product_dir = tmp_path / 'A.SAFE'
    product_dir.mkdir(parents=True)
    manifest = product_dir / 'manifest.safe'
    manifest.write_text('ok', encoding='utf-8')

    assert is_product_complete(str(product_dir))

    fpath = tmp_path / 'file.bin'
    fpath.write_bytes(b'abc')
    assert is_non_empty_file(str(fpath))

    empty_path = tmp_path / 'empty.bin'
    empty_path.write_bytes(b'')
    assert not is_non_empty_file(str(empty_path))

    missing = tmp_path / 'missing.bin'
    assert not is_non_empty_file(str(missing))

    os.remove(manifest)
    assert not is_product_complete(str(product_dir))


def test_is_product_complete_covers_every_product_layout(tmp_path):
    for name, manifest in (("a.SAFE", "manifest.safe"), ("b.SEN3", "xfdumanifest.xml"), ("c.SEN6", "xfdumanifest.xml")):
        folder = tmp_path / name
        folder.mkdir()
        (folder / "data.nc").write_text("x")
        assert not is_product_complete(str(folder))
        (folder / manifest).write_text("x")
        assert is_product_complete(str(folder))

    dem = tmp_path / "Copernicus_DSM_COG_30_N41_00_E012_00_DEM"
    dem.mkdir()
    assert not is_product_complete(str(dem))
    (dem / "empty.tif").write_text("")
    assert not is_product_complete(str(dem))
    (dem / "tile.tif").write_text("x")
    assert is_product_complete(str(dem))

    single = tmp_path / "S5P_X.nc"
    assert not is_product_complete(str(single))
    single.write_text("")
    assert not is_product_complete(str(single))
    single.write_text("x")
    assert is_product_complete(str(single))


def test_can_skip_download_needs_evidence_of_a_full_download(tmp_path):
    single = tmp_path / "S5P_X.nc"
    single.write_bytes(b"x" * 10)
    assert can_skip_download(str(single))
    assert can_skip_download(str(single), 10)
    assert can_skip_download(str(single), float("nan"))
    assert not can_skip_download(str(single), 1000)

    safe = tmp_path / "S1A_X.SAFE"
    safe.mkdir()
    (safe / "preview.png").write_bytes(b"x")
    assert not can_skip_download(str(safe))
    (safe / "manifest.safe").write_bytes(b"x")
    assert can_skip_download(str(safe), 123456)

    dem = tmp_path / "DEM1_X"
    dem.mkdir()
    (dem / "tile.tif").write_bytes(b"x")
    assert not can_skip_download(str(dem))
    assert is_product_complete(str(dem))
    assert not can_skip_download(str(tmp_path / "missing"))


def _download(tmp_path, s3_path, content_length):
    from phidown.search import CopernicusDataSearcher

    df = pd.DataFrame([{"Name": "product", "S3Path": s3_path, "ContentLength": content_length}])
    config = tmp_path / ".s5cfg"
    config.write_text("[default]\n")
    with patch("phidown.search.pull_down") as pull_down:
        summary = CopernicusDataSearcher().download_products(
            df=df, output_dir=str(tmp_path), config_file=str(config), mode="fast", verbose=False
        )
    return summary, pull_down


def test_download_products_fetches_a_truncated_file_again(tmp_path):
    (tmp_path / "S5P_X.nc").write_bytes(b"x")
    summary, pull_down = _download(tmp_path, "/eodata/Sentinel-5P/S5P_X.nc", 1000)
    assert pull_down.call_count == 1
    assert summary["skipped"] == 0


def test_download_products_skips_a_file_of_the_catalogue_size(tmp_path):
    (tmp_path / "S5P_X.nc").write_bytes(b"x" * 1000)
    summary, pull_down = _download(tmp_path, "/eodata/Sentinel-5P/S5P_X.nc", 1000)
    assert pull_down.call_count == 0
    assert summary["skipped"] == 1


def test_download_products_fetches_a_partial_folder_again(tmp_path):
    (tmp_path / "DEM1_X").mkdir()
    (tmp_path / "DEM1_X" / "tile.tif").write_bytes(b"x")
    summary, pull_down = _download(tmp_path, "/eodata/CCM/DEM1_X", 1000)
    assert pull_down.call_count == 1
    assert summary["skipped"] == 0


def test_download_products_safe_mode_leaves_a_partial_folder_to_the_resumable_download(tmp_path):
    from phidown.search import CopernicusDataSearcher

    (tmp_path / "DEM1_X").mkdir()
    (tmp_path / "DEM1_X" / "tile.tif").write_bytes(b"x")
    df = pd.DataFrame([{"Name": "product", "S3Path": "/eodata/CCM/DEM1_X", "ContentLength": 1000}])
    config = tmp_path / ".s5cfg"
    config.write_text("[default]\n")
    with patch("phidown.search.download_s3_resumable") as resumable:
        resumable.return_value.status = "success"
        resumable.return_value.output_path = str(tmp_path / "DEM1_X")
        summary = CopernicusDataSearcher().download_products(
            df=df, output_dir=str(tmp_path), config_file=str(config), mode="safe", verbose=False
        )
    assert resumable.call_count == 1
    assert summary["skipped"] == 0


def test_is_single_file_s3_path():
    assert is_single_file_s3_path("/eodata/Sentinel-5P/TROPOMI/L2__CO____/2024/06/08/S5P_X.nc")
    assert not is_single_file_s3_path("/eodata/Sentinel-1/SAR/IW_SLC__1S/2024/06/08/S1A_X.SAFE")
    assert not is_single_file_s3_path("/eodata/Sentinel-6/P4/2024/06/08/S6A_X.SEN6/")
    assert not is_single_file_s3_path("/eodata/CCM/COP-DEM/Copernicus_DSM_COG_30_N41_00_E012_00_DEM")
