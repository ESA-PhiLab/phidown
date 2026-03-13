"""Tests for package-level lazy exports and import boundaries."""

import builtins
import importlib
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def _clear_phidown_modules():
    removed = {}
    for module_name in list(sys.modules):
        if module_name == "phidown" or module_name.startswith("phidown."):
            removed[module_name] = sys.modules.pop(module_name)
    return removed


def test_importing_submodule_does_not_require_unrelated_runtime_deps(monkeypatch):
    original_import = builtins.__import__

    def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "pandas":
            raise ImportError("blocked pandas for lazy import test")
        return original_import(name, globals, locals, fromlist, level)

    removed = _clear_phidown_modules()
    monkeypatch.setattr(builtins, "__import__", guarded_import)

    try:
        module = importlib.import_module("phidown.download_state")
        assert module.default_state_file("/tmp").endswith(".phidown_download_state.json")
    finally:
        _clear_phidown_modules()
        sys.modules.update(removed)


def test_package_getattr_lazy_loads_known_exports(monkeypatch):
    import phidown

    monkeypatch.setitem(
        phidown._LAZY_EXPORTS,
        "download_state_file",
        ("phidown.download_state", "default_state_file"),
    )

    assert "download_state_file" not in phidown.__dict__
    assert phidown.download_state_file.__name__ == "default_state_file"


def test_package_getattr_rejects_unknown_exports():
    import phidown

    with pytest.raises(AttributeError):
        getattr(phidown, "does_not_exist")


def test_optional_exports_raise_helpful_import_error(monkeypatch):
    import phidown

    monkeypatch.setattr(phidown, "_dependencies_available", lambda dependencies: False)

    with pytest.raises(ImportError, match="optional dependencies"):
        getattr(phidown, "plot_kml_coordinates")
