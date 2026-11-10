#!/usr/bin/env bash
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
exec sudo python3 "$DIR/rpi4_fullchip.py" --label case-passivo_lab_2gb --freqs 1500 --fan-note 'Case dissipador passivo' "$@"
