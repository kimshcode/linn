#!/usr/bin/env bash
set -euo pipefail

LINN_HOME="${LINN_HOME:-$HOME/.linn}"
ZSHRC="${ZSHRC:-$HOME/.zshrc}"
START_MARKER="# >>> linn >>>"
END_MARKER="# <<< linn <<<"

if [[ -f "$ZSHRC" ]]; then
  tmp_file="$(mktemp)"
  awk -v start="$START_MARKER" -v end="$END_MARKER" '
    $0 == start {in_block=1; next}
    $0 == end {in_block=0; next}
    !in_block {print}
  ' "$ZSHRC" > "$tmp_file"
  mv "$tmp_file" "$ZSHRC"
fi

rm -rf "$LINN_HOME"
echo "Removed $LINN_HOME and linn shell integration from $ZSHRC"
echo "Restart shell or run: source \"$ZSHRC\""
