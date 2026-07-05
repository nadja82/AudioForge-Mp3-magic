#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
[[ -x .venv/bin/python ]] || { echo "Virtuelle Umgebung fehlt. Bitte zuerst ./install.sh ausführen."; exit 1; }
source .venv/bin/activate
python main.py
