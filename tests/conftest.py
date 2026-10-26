"""Pytest configuration for local-repo imports."""

from __future__ import annotations

import os
import sys


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


import pytest


@pytest.fixture(autouse=True)
def _clear_stac_collections_cache():
    """Keep the STAC collection list cache from leaking between tests."""
    from phidown import stac

    stac._COLLECTIONS_CACHE.clear()
    yield
    stac._COLLECTIONS_CACHE.clear()
