#!/usr/bin/env bash
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
exec sudo python3 "$DIR/rpi4_fullchip.py" --label torre-ventilada_server_8gb --freqs 1500,1800 --fan-note 'Torre ventilada - ventilador em funcionamento' "$@"
