"""Local agent skill installation helpers for phidown."""

import argparse
import json
import os
import shutil
import sys
from pathlib import Path
from typing import List, Optional, Sequence


SUPPORTED_ENGINES = ("codex", "claude", "cursor")
SKILL_NAME = "phidown"


def _package_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _default_source_dir() -> Path:
    root = _package_root()
    candidates = [
        root / "skills" / SKILL_NAME,
        root / "plugins" / SKILL_NAME / "skills" / SKILL_NAME,
        Path.cwd() / "skills" / SKILL_NAME,
    ]
    for candidate in candidates:
        if (candidate / "SKILL.md").is_file():
            return candidate
    raise FileNotFoundError(
        "Cannot find phidown skill assets. Expected skills/phidown/SKILL.md "
        "in the installed package or current repository."
    )


def _strip_frontmatter(text: str) -> str:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return text.strip()
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return "\n".join(lines[index + 1 :]).strip()
    return text.strip()


def _description_from_skill(text: str) -> str:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return "Use phidown to search and download Copernicus and PhiSat-2 data."
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if line.startswith("description:"):
            return line.split(":", 1)[1].strip().strip("\"'")
    return "Use phidown to search and download Copernicus and PhiSat-2 data."


def _copy_skill_dir(source_dir: Path, target_dir: Path) -> str:
    if not (source_dir / "SKILL.md").is_file():
        raise FileNotFoundError(f"Missing skill entrypoint: {source_dir / 'SKILL.md'}")
    if source_dir.resolve() == target_dir.resolve():
        return "already current"
    if target_dir.exists():
        if not target_dir.is_dir():
            raise FileExistsError(f"Target exists and is not a directory: {target_dir}")
        shutil.rmtree(target_dir)
    target_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source_dir, target_dir)
    return "installed"


def _remove_path(target: Path) -> str:
    if target.is_dir():
        shutil.rmtree(target)
        return "removed"
    if target.exists():
        target.unlink()
        return "removed"
    return "not installed"


def _codex_target() -> Path:
    return Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")) / "skills" / SKILL_NAME


def _claude_target() -> Path:
    return Path.home() / ".claude" / "skills" / SKILL_NAME


def _cursor_target(project_dir: Path) -> Path:
    return project_dir / ".cursor" / "rules" / f"{SKILL_NAME}.mdc"


def _cursor_rule_text(source_dir: Path) -> str:
    skill_text = (source_dir / "SKILL.md").read_text(encoding="utf-8")
    body = _strip_frontmatter(skill_text)
    description = _description_from_skill(skill_text)
    commands_path = source_dir / "references" / "commands.md"
    commands = ""
    if commands_path.is_file():
        commands = "\n\n## Command Patterns\n\n" + commands_path.read_text(encoding="utf-8").strip()
    return (
        "---\n"
        f"description: {json.dumps(description)}\n"
        "alwaysApply: false\n"
        "---\n\n"
        f"{body}{commands}\n"
    )


def _write_cursor_rule(source_dir: Path, target: Path) -> str:
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(_cursor_rule_text(source_dir), encoding="utf-8")
    return "installed"


def _expand_engines(engine: str) -> List[str]:
    return list(SUPPORTED_ENGINES) if engine == "all" else [engine]


def add_skill(engine: str, source_dir: Optional[Path] = None, cursor_project_dir: Optional[Path] = None) -> List[str]:
    source = source_dir or _default_source_dir()
    project_dir = cursor_project_dir or Path.cwd()
    messages: List[str] = []

    for selected in _expand_engines(engine):
        if selected == "codex":
            target = _codex_target()
            status = _copy_skill_dir(source, target)
            messages.append(f"{selected}: {status} at {target}")
        elif selected == "claude":
            target = _claude_target()
            status = _copy_skill_dir(source, target)
            messages.append(f"{selected}: {status} at {target}")
        elif selected == "cursor":
            target = _cursor_target(project_dir)
            status = _write_cursor_rule(source, target)
            messages.append(f"{selected}: {status} at {target}")
        else:
            raise ValueError(f"Unsupported engine: {selected}")
    return messages


def remove_skill(engine: str, cursor_project_dir: Optional[Path] = None) -> List[str]:
    project_dir = cursor_project_dir or Path.cwd()
    messages: List[str] = []

    for selected in _expand_engines(engine):
        if selected == "codex":
            target = _codex_target()
        elif selected == "claude":
            target = _claude_target()
        elif selected == "cursor":
            target = _cursor_target(project_dir)
        else:
            raise ValueError(f"Unsupported engine: {selected}")
        status = _remove_path(target)
        messages.append(f"{selected}: {status} at {target}")
    return messages


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="phidown skill",
        description="Install or remove phidown guidance for local agentic tools.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    for command in ("add", "remove"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument(
            "--engine",
            choices=(*SUPPORTED_ENGINES, "all"),
            default="codex",
            help="Agent engine to manage (default: codex). Use all for codex, claude, and cursor.",
        )
        subparser.add_argument(
            "--cursor-project-dir",
            type=Path,
            default=Path.cwd(),
            help="Project directory for Cursor .cursor/rules output (default: current directory).",
        )
        if command == "add":
            subparser.add_argument(
                "--source-dir",
                type=Path,
                help="Override source skill directory containing SKILL.md.",
            )
    return parser


def skill_main(argv: Optional[Sequence[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "add":
            messages = add_skill(args.engine, source_dir=args.source_dir, cursor_project_dir=args.cursor_project_dir)
        elif args.command == "remove":
            messages = remove_skill(args.engine, cursor_project_dir=args.cursor_project_dir)
        else:
            parser.error("Expected add or remove")
            return 2
    except Exception as exc:
        print(f"phidown skill {args.command} failed: {exc}", file=sys.stderr)
        return 1

    for message in messages:
        print(message)
    return 0


if __name__ == "__main__":
    sys.exit(skill_main())
