# linn

Small CLI to register and activate Python virtual environments by name.

## Behavior

- `linn <name> init`: create a venv with `uv` at `~/.linn/<name>`.
- `linn <name> <path_to_venv>`: register an existing venv path under a name.
- `linn <name> activate`: resolve the activation script path for the name.
- `linn make pdf`: build every `*.tex` file in the current directory into a PDF.
- `linn make key`: create an Ed25519 SSH key at `~/.ssh/id_ed25519`.
- `linn list`: list registered names and paths.
- `linn remove <name>`: remove `~/.linn/<name>`.

All mappings are stored under `~/.linn/<name>/venv_path.txt`.

## Commands

### `linn make pdf`

Build every `*.tex` file in the current directory into a PDF. Output filenames
keep the TeX basename with `.pdf` as the extension. Files starting with `00_`
are renamed to start with `zz_`, so `00_paper.tex` builds to `zz_paper.pdf`.

LaTeX helper files such as `.aux`, `.bbl`, `.blg`, `.log`, and `.out` are
removed after each successful build.

### `linn make key`

Create an Ed25519 SSH key pair in `~/.ssh`:

- Private key: `~/.ssh/id_ed25519`
- Public key: `~/.ssh/id_ed25519.pub`
- Key comment: `linn make key`
- Private key permissions: `600`
- Public key permissions: `644`

`~/.ssh` is created if needed with `700` permissions. Existing key files are
never overwritten; if either key file already exists, the command exits with an
error.

## Install

Run:

```bash
./install.sh
```

`install.sh` writes everything to `~/.linn`, installs shell integration into `~/.zshrc`,
and creates:

- `~/.linn/bin/linn`
- `~/.linn/bin/linn_cli.py`
- `~/.linn/linn.zsh`

After reloading the shell:

```bash
linn jordy init
linn jordy activate
cd /path/to/tex/files
linn make pdf
linn make key
```

## Uninstall

```bash
./uninstall.sh
```
