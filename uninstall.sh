#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
read -rp "AudioForge lokale .venv und Desktop-Starter entfernen? [j/N]: " answer
if echo "$answer" | grep -qiE "^(j|ja|y|yes)$"; then
  rm -rf .venv
  rm -f "$HOME/.local/share/applications/audioforge.desktop"
  echo "Lokale Installation entfernt."
else
  echo "Abgebrochen."
fi
