#!/usr/bin/env bash
set -uo pipefail
P=/sys/devices/system/cpu/cpufreq/policy0
echo '=== FULLCHIP DIAGNOSTICO V1.2 ==='
cat /proc/device-tree/model 2>/dev/null | tr -d '\000'; echo
uname -r
for f in cpuinfo_max_freq scaling_min_freq scaling_max_freq scaling_available_frequencies scaling_governor; do
  if [[ -f "$P/$f" ]]; then printf '%s: ' "$f"; cat "$P/$f"; fi
done
echo '=== FIRMWARE ==='
vcgencmd get_config int 2>/dev/null | grep -E 'arm_freq|arm_boost|over_voltage' || true
vcgencmd get_throttled 2>/dev/null || true
vcgencmd measure_temp 2>/dev/null || true
echo '=== GPU ==='
ls -la /dev/dri/ 2>/dev/null || true
lsmod | grep -E '^(vc4|v3d) ' || true
echo '=== EGL HEADLESS ==='
DIR="$(cd "$(dirname "$0")" && pwd)"
if [[ -x "$DIR/gpu_headless_v3d" ]]; then
 timeout -s TERM 12 "$DIR/gpu_headless_v3d" --width 640 --height 360 --seconds 3 2>&1 || true
else
 echo 'gpu_headless_v3d nao compilado: instale dependencias no pacote v1.2'
fi
echo '=== LOG ORIGINAL DA GPU ==='
LAST="$(find "$HOME/rpi4-fullchip-results" -name gpu_preflight.log -type f 2>/dev/null | sort | tail -n 1)"
if [[ -n "$LAST" ]]; then echo "$LAST"; tail -n 65 "$LAST"; fi
