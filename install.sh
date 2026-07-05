#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
APP_NAME="AudioForge"; VENV_DIR=".venv"
have_cmd(){ command -v "$1" >/dev/null 2>&1; }
detect_distro(){ [[ -f /etc/os-release ]] && { . /etc/os-release; echo "${ID:-unknown} ${ID_LIKE:-} ${NAME:-}"; } || echo unknown; }
install_debian(){ sudo apt update; sudo apt install -y python3 python3-pip python3-venv ffmpeg xdg-utils libxcb-cursor0 libxkbcommon-x11-0 libegl1; }
install_arch(){ sudo pacman -Syu --needed python python-pip python-virtualenv ffmpeg xdg-utils xcb-util-cursor xcb-util-keysyms xcb-util-renderutil xcb-util-wm libxkbcommon-x11; }
echo "====================================="; echo "  $APP_NAME Installer"; echo "====================================="; echo
echo "1) Ubuntu / Debian"; echo "2) CachyOS / Arch Linux"; echo "3) Automatisch erkennen"; echo "4) Systempakete überspringen"; echo
read -rp "Auswahl [1-4]: " choice
case "$choice" in
  1) install_debian;;
  2) install_arch;;
  3) distro="$(detect_distro)"; echo "Erkannt: $distro"; if echo "$distro" | grep -qiE "debian|ubuntu|linuxmint|pop"; then install_debian; elif echo "$distro" | grep -qiE "arch|cachyos|manjaro|endeavouros"; then install_arch; else echo "Distribution nicht erkannt."; exit 1; fi;;
  4) echo "Systempakete werden übersprungen.";;
  *) echo "Ungültige Auswahl."; exit 1;;
esac
py_cmd=python3; have_cmd python3 || py_cmd=python
"$py_cmd" -m venv "$VENV_DIR"
"$VENV_DIR/bin/python" -m pip install --upgrade pip wheel setuptools
"$VENV_DIR/bin/pip" install -r requirements.txt
cat > run.sh <<'RUN'
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
[[ -x .venv/bin/python ]] || { echo "Virtuelle Umgebung fehlt. Bitte ./install.sh ausführen."; exit 1; }
source .venv/bin/activate
python main.py
RUN
chmod +x run.sh
read -rp "Desktop-Starter im App-Menü erstellen? [j/N]: " answer
if echo "$answer" | grep -qiE "^(j|ja|y|yes)$"; then
  mkdir -p "$HOME/.local/share/applications"
  cat > "$HOME/.local/share/applications/audioforge.desktop" <<EOF
[Desktop Entry]
Name=AudioForge
Comment=Audio Converter mit Magic-Presets
Exec=$(pwd)/run.sh
Icon=$(pwd)/assets/icon.png
Terminal=false
Type=Application
Categories=Audio;AudioVideo;Utility;
EOF
fi
echo; echo "Installation abgeschlossen. Start: ./run.sh"
