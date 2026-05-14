#!/usr/bin/env python3
"""Per-environment Python venv registry and initialization tool."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


USAGE = """Usage:
  linn <name> <path_to_venv>
  linn <name> init
  linn <name> activate
  linn make pdf
  linn setup key
  linn setup gpg
  linn list
  linn remove <name>
"""

NAME_RE = re.compile(r"^[A-Za-z0-9._-]+$")
VENV_PATH_FILE = "venv_path.txt"
LATEX_ARTIFACT_SUFFIXES = (
    ".aux",
    ".bbl",
    ".blg",
    ".log",
    ".out",
    ".toc",
)
GPG_KEY_ID_RE = re.compile(r"[A-F0-9]{16}")


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


def init(name: str) -> int:
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
        print(f"Error: '{name}' is not registered. Run `linn {name} init` first.", file=sys.stderr)
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


def pdf_output_name(tex_path: Path) -> str:
    stem = tex_path.stem
    if stem.startswith("00_"):
        stem = f"zz_{stem[3:]}"
    return f"{stem}.pdf"


def run_build_step(args: list[str], cwd: Path) -> None:
    subprocess.run(args, cwd=cwd, check=True)


def run_text(args: list[str], check: bool = True) -> str:
    result = subprocess.run(
        args,
        check=check,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return result.stdout


def prompt(message: str, default: str | None = None) -> str:
    value = input(message)
    if not value and default is not None:
        return default
    return value


def prompt_yes_no(message: str, default: bool) -> bool:
    suffix = " [Y/n] " if default else " [y/N] "
    value = prompt(f"{message}{suffix}").strip().lower()
    if not value:
        return default
    return value.startswith("y")


def cleanup_latex_artifacts(directory: Path, base: str) -> None:
    for suffix in LATEX_ARTIFACT_SUFFIXES:
        artifact = directory / f"{base}{suffix}"
        try:
            artifact.unlink()
        except FileNotFoundError:
            pass


def tex_uses_bibtex(aux_path: Path) -> bool:
    try:
        return "\\bibdata" in aux_path.read_text(encoding="utf-8", errors="ignore")
    except FileNotFoundError:
        return False


def build_pdf(tex_path: Path) -> None:
    directory = tex_path.parent
    tex_name = tex_path.name
    base = tex_path.stem

    run_build_step(
        ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", tex_name],
        directory,
    )
    if tex_uses_bibtex(directory / f"{base}.aux"):
        run_build_step(["bibtex", base], directory)
    run_build_step(
        ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", tex_name],
        directory,
    )
    run_build_step(
        ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", tex_name],
        directory,
    )

    source_pdf = directory / f"{base}.pdf"
    target_pdf = directory / pdf_output_name(tex_path)
    if source_pdf != target_pdf:
        source_pdf.replace(target_pdf)

    cleanup_latex_artifacts(directory, base)


def make_pdf() -> int:
    tex_files = sorted(Path.cwd().glob("*.tex"), key=lambda path: path.name)
    if not tex_files:
        print("Error: no TeX files found in the current directory.", file=sys.stderr)
        return 1

    try:
        for tex_path in tex_files:
            print(f"Building {tex_path.name} -> {pdf_output_name(tex_path)}")
            build_pdf(tex_path)
    except FileNotFoundError as exc:
        command = exc.filename or "required command"
        print(f"Error: '{command}' command not found.", file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as exc:
        print(f"Error: build failed with exit code {exc.returncode}.", file=sys.stderr)
        return 1

    return 0


def setup_key() -> int:
    ssh_dir = Path.home() / ".ssh"
    private_key = ssh_dir / "id_ed25519"
    public_key = ssh_dir / "id_ed25519.pub"

    if private_key.exists() or public_key.exists():
        print(
            f"Error: SSH key already exists at {private_key} or {public_key}.",
            file=sys.stderr,
        )
        return 1

    try:
        ssh_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        ssh_dir.chmod(0o700)
        subprocess.run(
            [
                "ssh-keygen",
                "-t",
                "ed25519",
                "-f",
                str(private_key),
                "-C",
                "linn setup key",
                "-N",
                "",
            ],
            check=True,
        )
        private_key.chmod(0o600)
        public_key.chmod(0o644)
    except FileNotFoundError:
        print("Error: 'ssh-keygen' command not found.", file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as exc:
        print(f"Error: ssh-keygen failed with exit code {exc.returncode}.", file=sys.stderr)
        return 1

    print(f"Created SSH key: {private_key}")
    print(f"Created SSH public key: {public_key}")
    return 0


def gpg_version_supports_ed25519(version_output: str) -> bool:
    match = re.search(r"(\d+)\.(\d+)", version_output)
    if not match:
        return False
    major, minor = int(match.group(1)), int(match.group(2))
    return (major, minor) >= (2, 1)


def extract_gpg_key_id(secret_keys_output: str) -> str | None:
    for line in secret_keys_output.splitlines():
        if line.lstrip().startswith(("sec", "ssb")):
            match = GPG_KEY_ID_RE.search(line)
            if match:
                return match.group(0)
    return None


def generated_gpg_key_id(email: str) -> str | None:
    output = run_text(
        ["gpg", "--list-secret-keys", "--keyid-format", "long", email],
        check=False,
    )
    return extract_gpg_key_id(output)


def append_missing_gpg_agent_config(gpg_agent_conf: Path) -> None:
    existing = ""
    try:
        existing = gpg_agent_conf.read_text(encoding="utf-8")
    except FileNotFoundError:
        pass

    additions: list[str] = []
    if "pinentry-program" not in existing:
        pinentry_mac = shutil.which("pinentry-mac")
        if pinentry_mac:
            additions.append(f"pinentry-program {pinentry_mac}")
            print("Configured pinentry-mac for passphrase prompts.")
        else:
            print("Tip: brew install pinentry-mac for a native macOS passphrase dialog.")

    if "default-cache-ttl" not in existing:
        additions.extend(["default-cache-ttl 3600", "max-cache-ttl 86400"])
        print("Set passphrase cache TTL: 1h default, 24h max.")

    if additions:
        gpg_agent_conf.parent.mkdir(parents=True, exist_ok=True)
        with gpg_agent_conf.open("a", encoding="utf-8") as handle:
            if existing and not existing.endswith("\n"):
                handle.write("\n")
            handle.write("\n".join(additions))
            handle.write("\n")


def maybe_add_gpg_tty_to_zshrc() -> None:
    zshrc = Path(os.environ.get("ZSHRC", str(Path.home() / ".zshrc"))).expanduser()
    try:
        zshrc_text = zshrc.read_text(encoding="utf-8")
    except FileNotFoundError:
        zshrc_text = ""

    if "GPG_TTY" in zshrc_text:
        return

    print("")
    print("Add this to your ~/.zshrc for terminal passphrase prompts:")
    print("  export GPG_TTY=$(tty)")
    if prompt_yes_no("Add it now?", True):
        with zshrc.open("a", encoding="utf-8") as handle:
            if zshrc_text and not zshrc_text.endswith("\n"):
                handle.write("\n")
            handle.write("\nexport GPG_TTY=$(tty)\n")
        print(f"Added GPG_TTY to {zshrc}.")


def setup_gpg() -> int:
    missing = [command for command in ("gpg", "git") if shutil.which(command) is None]
    if missing:
        for command in missing:
            print(f"Error: '{command}' is not installed.", file=sys.stderr)
            if command == "gpg":
                print("Install with: brew install gnupg", file=sys.stderr)
        return 1

    print("GPG commit signing setup")
    print("")

    try:
        existing_keys = run_text(
            ["gpg", "--list-secret-keys", "--keyid-format", "long"],
            check=False,
        )
        use_existing = False
        if existing_keys.strip():
            print("Existing GPG keys found:")
            print(existing_keys.rstrip())
            print("")
            use_existing = prompt_yes_no("Use an existing key?", False)

        if use_existing:
            key_id = prompt("Enter the key ID (the hex string after sec rsa/ed25519): ").strip()
            if not key_id:
                print("Error: key ID is required.", file=sys.stderr)
                return 1
        else:
            print("Generating a new GPG key")
            full_name = prompt("Full name (for key identity): ").strip()
            email = prompt("Email address (must match your Git commits): ").strip()
            if not full_name or not email:
                print("Error: full name and email are required.", file=sys.stderr)
                return 1

            version_output = run_text(["gpg", "--version"])
            if gpg_version_supports_ed25519(version_output):
                print("Using Ed25519.")
                subprocess.run(
                    [
                        "gpg",
                        "--batch",
                        "--passphrase",
                        "",
                        "--quick-gen-key",
                        f"{full_name} <{email}>",
                        "ed25519",
                        "sign",
                        "0",
                    ],
                    check=True,
                )
            else:
                print("Using RSA-4096.")
                batch_config = "\n".join(
                    [
                        "Key-Type: RSA",
                        "Key-Length: 4096",
                        f"Name-Real: {full_name}",
                        f"Name-Email: {email}",
                        "Expire-Date: 0",
                        "%no-protection",
                        "%commit",
                        "",
                    ]
                )
                subprocess.run(
                    ["gpg", "--batch", "--gen-key"],
                    input=batch_config,
                    text=True,
                    check=True,
                )

            key_id = generated_gpg_key_id(email)
            if not key_id:
                print("Error: failed to retrieve the generated key ID.", file=sys.stderr)
                return 1
            print(f"Key generated: {key_id}")

        print("")
        print(f"Configuring Git to use GPG key {key_id}")
        scope = ["--global"] if prompt_yes_no("Apply globally?", True) else []
        gpg_path = shutil.which("gpg")
        if gpg_path is None:
            print("Error: 'gpg' is not installed.", file=sys.stderr)
            return 1

        subprocess.run(["git", "config", *scope, "user.signingkey", key_id], check=True)
        subprocess.run(["git", "config", *scope, "commit.gpgsign", "true"], check=True)
        subprocess.run(["git", "config", *scope, "tag.gpgsign", "true"], check=True)
        subprocess.run(["git", "config", *scope, "gpg.program", gpg_path], check=True)
        print("Git config updated: commit.gpgsign=true, tag.gpgsign=true.")

        gpg_home = Path(
            os.environ.get("GNUPGHOME", str(Path.home() / ".gnupg"))
        ).expanduser()
        append_missing_gpg_agent_config(gpg_home / "gpg-agent.conf")
        if shutil.which("gpg-connect-agent"):
            subprocess.run(
                ["gpg-connect-agent", "reloadagent", "/bye"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )

        print("")
        print("Your GPG public key (add this to GitHub/GitLab):")
        print("")
        print(run_text(["gpg", "--armor", "--export", key_id]).rstrip())
        print("")
        print("Setup complete.")
        print("")
        print("Next steps:")
        print("1. Add the public key above to your Git host.")
        print("2. Test with: git commit --allow-empty -m 'test gpg signing'")
        print("3. Verify with: git log --show-signature -1")

        maybe_add_gpg_tty_to_zshrc()
        return 0
    except FileNotFoundError as exc:
        command = exc.filename or "required command"
        print(f"Error: '{command}' command not found.", file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as exc:
        command = exc.cmd[0] if isinstance(exc.cmd, list) and exc.cmd else "command"
        print(f"Error: {command} failed with exit code {exc.returncode}.", file=sys.stderr)
        return 1


def main(argv: list[str]) -> int:
    if len(argv) == 3 and argv[1] == "make" and argv[2] == "pdf":
        return make_pdf()

    if len(argv) == 3 and argv[1] == "setup" and argv[2] == "key":
        return setup_key()

    if len(argv) == 3 and argv[1] == "setup" and argv[2] == "gpg":
        return setup_gpg()

    if len(argv) == 2 and argv[1] == "list":
        return list_envs()

    if len(argv) == 3 and argv[1] == "remove":
        return remove_env(argv[2])

    if len(argv) == 3 and argv[2] == "init":
        return init(argv[1])

    if len(argv) == 3 and argv[2] == "activate":
        return activation_script(argv[1])

    if len(argv) == 3:
        return register(argv[1], argv[2])

    print(USAGE.strip(), file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
