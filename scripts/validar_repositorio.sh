#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
echo '=== Verificando scripts Bash ==='
for f in instalar_dependencias.sh diagnostico_rapido.sh diagnostico_frequencia_1500.sh testar_2gb_case.sh testar_8gb_torre.sh scripts/validar_repositorio.sh; do
  bash -n "$f"
  echo "OK shell: $f"
done
echo '=== Verificando sintaxe Python ==='
python3 - <<'PYCODE'
import ast
from pathlib import Path
for name in ['rpi4_fullchip.py','comparar.py','tests/test_pure_functions.py']:
    ast.parse(Path(name).read_text(encoding='utf-8'),filename=name)
    print('OK Python:',name)
PYCODE
echo '=== Testes unitarios sem hardware ==='
python3 -m unittest discover -s tests -p 'test_*.py' -v
echo '=== Politica editorial README ==='
python3 - <<'PYCODE'
from pathlib import Path
s=Path('README.md').read_text(encoding='utf-8')
assert not any(line.strip()=='---' for line in s.splitlines()), 'Nao usar separador horizontal --- no README'
assert 'https://elcereza.com/blog/raspberry-pi-4-dissipacao-ativa-ou-passiva-qual-usar' in s
assert 'https://elcereza.com/projects/raspberry-pi-4-teste-estresse-cpu-gpu-ram' in s
assert 'github.com/elcereza/FullChip-Benchmark' in s
print('OK: padrao README e links cruzados')
PYCODE
echo 'Verificacoes concluidas. Hardware V3D/cpufreq nao foi testado por este script.'
