"""Download state persistence helpers for resumable workflows."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def utc_now_iso() -> str:
    """Return the current UTC timestamp as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


def default_state_file(output_dir: str) -> str:
    """Return the default state file path for an output directory.
    
    The state file is stored in a .phidown subdirectory to keep
    download metadata separate from downloaded products.
    """
    state_dir = Path(output_dir) / '.phidown'
    state_dir.mkdir(parents=True, exist_ok=True)
    return str(state_dir / 'download_state.json')


def is_product_complete(product_dir: str) -> bool:
    """Check if a SAFE product directory looks complete."""
    if not os.path.isdir(product_dir):
        return False
    return os.path.exists(os.path.join(product_dir, 'manifest.safe'))


def is_non_empty_file(path: str) -> bool:
    """Check if file exists and has non-zero size."""
    return os.path.isfile(path) and os.path.getsize(path) > 0


class DownloadStateStore:
    """Simple JSON-backed state store for download checkpoints."""

    def __init__(self, state_file: str):
        self.path = Path(state_file)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._state: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, Any]:
        if not self.path.exists():
            return {'items': {}}

        try:
            raw = json.loads(self.path.read_text(encoding='utf-8'))
        except Exception as exc:
            logger.warning(f'Failed to read state file {self.path}: {exc}. Reinitializing state.')
            return {'items': {}}

        if not isinstance(raw, dict):
            return {'items': {}}
        items = raw.get('items')
        if not isinstance(items, dict):
            return {'items': {}}
        return {'items': items}

    def _persist(self) -> None:
        payload = json.dumps(self._state, indent=2, sort_keys=True)
        tmp_path = self.path.with_suffix(self.path.suffix + '.tmp')
        tmp_path.write_text(payload, encoding='utf-8')
        os.replace(tmp_path, self.path)

    def get(self, item_id: str) -> Optional[Dict[str, Any]]:
        return self._state['items'].get(str(item_id))

    def set(self, item_id: str, record: Dict[str, Any]) -> None:
        self._state['items'][str(item_id)] = record
        self._persist()

    def mark(
        self,
        item_id: str,
        status: str,
        *,
        attempts: Optional[int] = None,
        error: Optional[str] = None,
        output_path: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        existing = self.get(item_id) or {}
        record: Dict[str, Any] = {
            'status': status,
            'updated_at': utc_now_iso(),
        }

        if attempts is not None:
            record['attempts'] = int(attempts)
        elif 'attempts' in existing:
            record['attempts'] = existing['attempts']

        if error is not None:
            record['error'] = error
        elif 'error' in existing and status != 'success':
            record['error'] = existing['error']

        if output_path is not None:
            record['output_path'] = output_path
        elif 'output_path' in existing:
            record['output_path'] = existing['output_path']

        if extra:
            record.update(extra)

        self.set(item_id, record)
