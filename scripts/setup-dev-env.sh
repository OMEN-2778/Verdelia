#!/usr/bin/env bash
# Installs the Godot editor binary used by this project (and by the godot MCP server in .mcp.json).
# Safe to re-run: does nothing when the pinned version is already on PATH.
set -euo pipefail

GODOT_VERSION="4.7.2"
INSTALL_DIR="${GODOT_INSTALL_DIR:-/opt/godot}"
BIN_DIR="${GODOT_BIN_DIR:-/usr/local/bin}"

if command -v godot >/dev/null 2>&1 && godot --headless --version 2>/dev/null | grep -q "^${GODOT_VERSION}\.stable"; then
  exit 0
fi

case "$(uname -s)-$(uname -m)" in
  Linux-x86_64) asset="Godot_v${GODOT_VERSION}-stable_linux.x86_64" ;;
  Linux-aarch64) asset="Godot_v${GODOT_VERSION}-stable_linux.arm64" ;;
  *) echo "setup-dev-env: install Godot ${GODOT_VERSION} manually from https://godotengine.org/download" >&2; exit 0 ;;
esac

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
curl -fsSL -o "$tmp/godot.zip" \
  "https://github.com/godotengine/godot/releases/download/${GODOT_VERSION}-stable/${asset}.zip"
unzip -oq "$tmp/godot.zip" -d "$tmp"
mkdir -p "$INSTALL_DIR" "$BIN_DIR"
install -m 755 "$tmp/$asset" "$INSTALL_DIR/$asset"
ln -sf "$INSTALL_DIR/$asset" "$BIN_DIR/godot"
echo "setup-dev-env: installed $(godot --headless --version)"
