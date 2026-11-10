#!/usr/bin/env bash
set -Eeuo pipefail
P=/sys/devices/system/cpu/cpufreq/policy0
if [[ "$(id -u)" != 0 ]]; then echo 'Execute: sudo bash diagnostico_frequencia_1500.sh' >&2; exit 2; fi
[[ -f "$P/scaling_max_freq" && -f "$P/scaling_min_freq" ]] || { echo 'politica CPU ausente' >&2; exit 2; }
ORIG_MIN=$(cat "$P/scaling_min_freq")
ORIG_MAX=$(cat "$P/scaling_max_freq")
restore() {
    trap - EXIT INT TERM
    printf '%s' "$ORIG_MAX" > "$P/scaling_max_freq" || true
    printf '%s' "$ORIG_MIN" > "$P/scaling_min_freq" || true
    echo '=== RESTAURACAO ==='
    echo "min=$(cat "$P/scaling_min_freq") max=$(cat "$P/scaling_max_freq")"
    if [[ "$(cat "$P/scaling_max_freq")" != "$ORIG_MAX" || "$(cat "$P/scaling_min_freq")" != "$ORIG_MIN" ]]; then
       echo 'ATENCAO: clock nao restaurado. Verifique politica cpufreq.' >&2
    fi
}
trap restore EXIT INT TERM
printf '=== ANTES ===\n'
for f in cpuinfo_max_freq scaling_min_freq scaling_max_freq scaling_cur_freq scaling_governor; do
    echo "$f=$(cat "$P/$f")"
done
if (( ORIG_MAX < 1500000 )); then
    echo 'Limite atual inferior a 1500MHz: nao vou elevar automaticamente.' >&2
    exit 2
fi
if (( ORIG_MIN > 1500000 )); then
    echo 'Minimo ultrapassa 1500MHz; reduzindo minimo temporariamente.'
    echo 600000 > "$P/scaling_min_freq"
fi
printf '1500000' > "$P/scaling_max_freq"
sleep 0.6
printf '=== APOS 0,6 s ===\n'
for f in scaling_min_freq scaling_max_freq scaling_cur_freq; do echo "$f=$(cat "$P/$f")"; done
sleep 2
printf '=== APOS 2,6 s ===\n'
for f in scaling_min_freq scaling_max_freq scaling_cur_freq; do echo "$f=$(cat "$P/$f")"; done
