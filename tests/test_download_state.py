"""Tests for download state persistence and helpers."""

import os
from datetime import datetime, timezone

from phidown.download_state import (
    DownloadStateStore,
    default_state_file,
    is_non_empty_file,
    is_product_complete,
    utc_now_iso,
)


def test_default_state_file_path(tmp_path):
    out = default_state_file(str(tmp_path))
    assert out.endswith('.phidown_download_state.json')


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
