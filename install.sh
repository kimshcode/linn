#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LINN_HOME="${LINN_HOME:-$HOME/.linn}"
BIN_DIR="$LINN_HOME/bin"
CLI_PATH="$BIN_DIR/linn_cli.py"
RUNNER_PATH="$BIN_DIR/linn"
ZSH_INTEGRATION="$LINN_HOME/linn.zsh"
ZSHRC="${ZSHRC:-$HOME/.zshrc}"
START_MARKER="# >>> linn >>>"
END_MARKER="# <<< linn <<<"

mkdir -p "$BIN_DIR"

cp "$SCRIPT_DIR/linn_cli.py" "$CLI_PATH"
chmod +x "$CLI_PATH"

cat > "$RUNNER_PATH" <<EOF
#!/usr/bin/env bash
exec env LINN_HOME="$LINN_HOME" python3 "$CLI_PATH" "\$@"
EOF
chmod +x "$RUNNER_PATH"

cat > "$ZSH_INTEGRATION" <<EOF
# shellcheck shell=bash
# Auto-loaded from ~/.zshrc

linn() {
  if [[ "\$#" -eq 2 && "\$2" == "activate" ]]; then
    local activate_script
    activate_script="\$(LINN_HOME="$LINN_HOME" python3 "$CLI_PATH" "\$1" activate)" || return \$?
    # shellcheck disable=SC1090
    source "\$activate_script"
  else
    LINN_HOME="$LINN_HOME" python3 "$CLI_PATH" "\$@"
  fi
}
EOF

touch "$ZSHRC"
if ! grep -Fq "$START_MARKER" "$ZSHRC"; then
  {
    echo ""
    echo "$START_MARKER"
    echo "source \"$ZSH_INTEGRATION\""
    echo "$END_MARKER"
  } >> "$ZSHRC"
fi

echo "Installed linn files under: $LINN_HOME"
echo "1) Open a new shell (or run: source \"$ZSHRC\")."
echo "2) Create managed env with uv: linn jordy init"
echo "   (creates $LINN_HOME/jordy)"
echo "3) Or register existing venv: linn jordy /Users/ekimsen/Library/CloudStorage/Dropbox/project/jordy/.venv"
echo "4) Activate it: linn jordy activate"
echo "5) Build TeX files in the current directory: linn make pdf"
echo "6) Create an Ed25519 SSH key: linn setup key"
echo "7) Configure GPG commit signing: linn setup gpg"
