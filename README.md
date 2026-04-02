# linn

Small CLI to register and activate Python virtual environments by name.

## Behavior

- `linn <name> setup`: create a venv with `uv` at `~/.linn/<name>`.
- `linn <name> <path_to_venv>`: register an existing venv path under a name.
- `linn <name> activate`: resolve the activation script path for the name.
- `linn list`: list registered names and paths.
- `linn remove <name>`: remove `~/.linn/<name>`.

All mappings are stored under `~/.linn/<name>/venv_path.txt`.

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
linn jordy setup
linn jordy activate
```

## Uninstall

```bash
./uninstall.sh
```
