#!/usr/bin/env python3
"""Per-environment Python venv registry and setup tool."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


USAGE = """Usage:
  linn <name> <path_to_venv>
  linn <name> setup
  linn <name> activate
  linn list
  linn remove <name>
"""

NAME_RE = re.compile(r"^[A-Za-z0-9._-]+$")
VENV_PATH_FILE = "venv_path.txt"


def linn_home() -> Path:
    base = Path.home() / ".linn"
    return Path(os.environ.get("LINN_HOME", str(base))).expanduser()


def env_dir(name: str) -> Path:
    return linn_home() / name


def env_path_file(name: str) -> Path:
    return env_dir(name) / VENV_PATH_FILE


def validate_name(name: str) -> str:
    if not NAME_RE.fullmatch(name):
        raise ValueError(
            "name must match [A-Za-z0-9._-] and cannot contain path separators."
        )
    return name


def resolve_venv_path(raw_path: str) -> Path:
    venv_path = Path(raw_path).expanduser().resolve()
    activate_script = venv_path / "bin" / "activate"
    if not activate_script.exists():
        raise ValueError(
            f"'{venv_path}' does not look like a Python venv (missing {activate_script})."
        )
    return venv_path


def store_mapping(name: str, venv_path: Path) -> None:
    directory = env_dir(name)
    directory.mkdir(parents=True, exist_ok=True)
    env_path_file(name).write_text(f"{venv_path}\n", encoding="utf-8")


def read_mapping(name: str) -> Path | None:
    mapping_file = env_path_file(name)
    if mapping_file.exists():
        value = mapping_file.read_text(encoding="utf-8").strip()
        if value:
            return Path(value).expanduser()

    managed_path = env_dir(name)
    if (managed_path / "bin" / "activate").exists():
        return managed_path

    return None


def register(name: str, raw_path: str) -> int:
    try:
        validate_name(name)
        venv_path = resolve_venv_path(raw_path)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    store_mapping(name, venv_path)
    print(f"Registered '{name}' -> {venv_path}")
    return 0


def setup(name: str) -> int:
    try:
        validate_name(name)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    target = env_dir(name)
    target.parent.mkdir(parents=True, exist_ok=True)

    try:
        subprocess.run(["uv", "venv", str(target)], check=True)
    except FileNotFoundError:
        print("Error: 'uv' command not found. Install uv first.", file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as exc:
        print(f"Error: uv failed with exit code {exc.returncode}.", file=sys.stderr)
        return 1

    store_mapping(name, target.resolve())
    print(f"Created environment '{name}' at {target}")
    return 0


def activation_script(name: str) -> int:
    try:
        validate_name(name)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    venv_path = read_mapping(name)
    if venv_path is None:
        print(f"Error: '{name}' is not registered. Run `linn {name} setup` first.", file=sys.stderr)
        return 1

    try:
        resolved = resolve_venv_path(str(venv_path))
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(str((resolved / "bin" / "activate").resolve()))
    return 0


def list_envs() -> int:
    home = linn_home()
    if not home.exists():
        print("No environments registered.")
        return 0

    rows: list[tuple[str, str]] = []
    for entry in sorted(home.iterdir(), key=lambda p: p.name):
        if not entry.is_dir():
            continue
        if entry.name == "bin":
            continue

        mapping_file = entry / VENV_PATH_FILE
        if mapping_file.exists():
            venv_path = mapping_file.read_text(encoding="utf-8").strip()
            if venv_path:
                rows.append((entry.name, venv_path))
                continue

        if (entry / "bin" / "activate").exists():
            rows.append((entry.name, str(entry.resolve())))

    if not rows:
        print("No environments registered.")
        return 0

    longest = max(len(name) for name, _ in rows)
    for name, venv_path in rows:
        print(f"{name.ljust(longest)}  {venv_path}")
    return 0


def remove_env(name: str) -> int:
    try:
        validate_name(name)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    target = env_dir(name)
    if not target.exists():
        print(f"Error: '{name}' is not registered.", file=sys.stderr)
        return 1

    shutil.rmtree(target)
    print(f"Removed '{name}' ({target})")
    return 0


def main(argv: list[str]) -> int:
    if len(argv) == 2 and argv[1] == "list":
        return list_envs()

    if len(argv) == 3 and argv[1] == "remove":
        return remove_env(argv[2])

    if len(argv) == 3 and argv[2] == "setup":
        return setup(argv[1])

    if len(argv) == 3 and argv[2] == "activate":
        return activation_script(argv[1])

    if len(argv) == 3:
        return register(argv[1], argv[2])

    print(USAGE.strip(), file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
