"""Tests for local agent skill installation CLI."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from phidown.cli import main
from phidown import skill_cli
from phidown.skill_cli import skill_main


def test_add_codex_installs_phidown_skill(monkeypatch, tmp_path):
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / "codex"))

    assert skill_main(["add", "--engine", "codex"]) == 0

    target = tmp_path / "codex" / "skills" / "phidown"
    assert (target / "SKILL.md").is_file()
    assert (target / "references" / "commands.md").is_file()
    assert (target / "agents" / "openai.yaml").is_file()


def test_add_all_installs_codex_claude_and_cursor(monkeypatch, tmp_path):
    home = tmp_path / "home"
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.setenv("CODEX_HOME", str(home / ".codex"))
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.chdir(project)

    assert skill_main(["add", "--engine", "all"]) == 0

    assert (home / ".codex" / "skills" / "phidown" / "SKILL.md").is_file()
    assert (home / ".claude" / "skills" / "phidown" / "SKILL.md").is_file()

    cursor_rule = project / ".cursor" / "rules" / "phidown.mdc"
    assert cursor_rule.is_file()
    assert "description:" in cursor_rule.read_text(encoding="utf-8")
    assert "Phidown" in cursor_rule.read_text(encoding="utf-8")


def test_claude_install_uses_home_env_when_available(monkeypatch, tmp_path):
    home = tmp_path / "home"
    fallback_home = tmp_path / "fallback-home"
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setattr(skill_cli.Path, "home", lambda: fallback_home)

    assert skill_main(["add", "--engine", "claude"]) == 0

    assert (home / ".claude" / "skills" / "phidown" / "SKILL.md").is_file()
    assert not (fallback_home / ".claude" / "skills" / "phidown").exists()


def test_remove_all_removes_installed_targets(monkeypatch, tmp_path):
    home = tmp_path / "home"
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.setenv("CODEX_HOME", str(home / ".codex"))
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.chdir(project)

    assert skill_main(["add", "--engine", "all"]) == 0
    assert skill_main(["remove", "--engine", "all"]) == 0

    assert not (home / ".codex" / "skills" / "phidown").exists()
    assert not (home / ".claude" / "skills" / "phidown").exists()
    assert not (project / ".cursor" / "rules" / "phidown.mdc").exists()


def test_main_dispatches_skill_subcommand(monkeypatch, tmp_path):
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / "codex"))

    with patch.object(sys, "argv", ["phidown", "skill", "add", "--engine", "codex"]):
        with pytest.raises(SystemExit) as exc_info:
            main()

    assert exc_info.value.code == 0
    assert (tmp_path / "codex" / "skills" / "phidown" / "SKILL.md").is_file()
