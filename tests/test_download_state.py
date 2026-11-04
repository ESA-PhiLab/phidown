"""Tests for download state persistence and helpers."""

import os
from datetime import datetime, timezone

from phidown.download_state import (
    DownloadStateStore,
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


def test_is_single_file_s3_path():
    assert is_single_file_s3_path("/eodata/Sentinel-5P/TROPOMI/L2__CO____/2024/06/08/S5P_X.nc")
    assert not is_single_file_s3_path("/eodata/Sentinel-1/SAR/IW_SLC__1S/2024/06/08/S1A_X.SAFE")
    assert not is_single_file_s3_path("/eodata/Sentinel-6/P4/2024/06/08/S6A_X.SEN6/")
    assert not is_single_file_s3_path("/eodata/CCM/COP-DEM/Copernicus_DSM_COG_30_N41_00_E012_00_DEM")
