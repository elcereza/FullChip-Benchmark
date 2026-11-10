# Instalação detalhada

Este roteiro complementa o [README principal](../README.md). O processo exige **um Raspberry Pi 4 real**, distribuição Debian/Raspberry Pi OS com APT, privilégios administrativos para instalação e fonte adequada.

## 1. Prepare o sistema

Use terminal local ou SSH. Antes de instalar pacotes, avalie serviços em funcionamento e reservas de manutenção; o benchmark pode afetar desempenho e estabilidade em condições inadequadas.

```bash
cat /proc/device-tree/model
uname -a
vcgencmd get_throttled
vcgencmd measure_temp
```

A primeira linha deve identificar Raspberry Pi 4 Model B. Se houver subtensão ativa, não avance para carga de estresse.

## 2. Clone e instale

```bash
sudo apt update
sudo apt install -y git
git clone https://github.com/elcereza/FullChip-Benchmark.git
cd FullChip-Benchmark
sudo bash instalar_dependencias.sh
```

O instalador verifica se o hardware é Pi 4, atualiza índices APT, instala ferramentas e compila `gpu_headless_v3d` com EGL/GLESv2/GBM. **Não copie o binário compilado de outro Raspberry**, mesmo quando a arquitetura parecer equivalente.

## 3. Faça o diagnóstico da GPU

```bash
bash diagnostico_rapido.sh
./gpu_headless_v3d --width 640 --height 360 --seconds 3
```

Espere `GL_RENDERER: V3D` e contagem positiva de `GPU_DRAW_FRAMES:`. Sem isso, o desempenho gráfico não foi validado; consulte o guia de problemas.

## 4. Faça um teste controlado antes da bateria longa

```bash
# Perfil lab, 1,5 GHz
bash testar_2gb_case.sh --stages cpu_single --smoke
bash testar_2gb_case.sh --stages gpu_3d --smoke
```

No perfil de servidor, substitua pelos comandos de `testar_8gb_torre.sh --freqs 1500`, um estágio por vez. Se algum teste for interrompido por subtensão, corrija fonte/cabo/conexões antes de voltar à carga.

## 5. Execute bateria completa, quando seguro

```bash
# Perfil de laboratório
bash testar_2gb_case.sh

# Perfil de servidor, depois de validar suporte de 1,8 GHz
sudo bash diagnostico_frequencia_1500.sh
bash testar_8gb_torre.sh
```

Esses comandos descrevem **máquinas distintas**: não rode os dois perfis ao mesmo tempo no mesmo Raspberry. Os resultados ficam em `~/rpi4-fullchip-results/` e a restauração dos limites originais aparece ao final da saída.
