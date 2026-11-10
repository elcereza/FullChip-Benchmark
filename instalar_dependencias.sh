#!/usr/bin/env bash
set -euo pipefail
if [[ $(id -u) -ne 0 ]]; then echo 'Execute com sudo' >&2; exit 2; fi
if [[ ! -f /proc/device-tree/model ]] || ! grep -a -q 'Raspberry Pi 4' /proc/device-tree/model; then echo 'Somente Pi 4' >&2; exit 3; fi
apt-get update
apt-get install -y stress-ng glmark2-es2-drm build-essential libegl-dev libgles-dev libgbm-dev
DIR="$(cd "$(dirname "$0")" && pwd)"
cc -O2 -Wall -Wextra -std=c11 "$DIR/gpu_headless_v3d.c" -o "$DIR/gpu_headless_v3d" -lEGL -lGLESv2 -lgbm -lm
chmod 0755 "$DIR/gpu_headless_v3d"
echo 'Dependencias prontas. Verifique GPU com ./gpu_headless_v3d --seconds 3'
