# Arquitetura do FullChip Benchmark

## Objetivo

Gerar cargas repetíveis para comparar sistemas de dissipação do Raspberry Pi 4 e obter séries temporais de temperatura/clocks/indicadores de proteção. A ferramenta não busca criar um ranking genérico de desempenho.

## Fluxo principal

```text
Pré-flight e diagnóstico
   ↓
Validação GPU V3D real
   ↓
Captura dos limites de cpufreq e aplicação de alvo permitido
   ↓
Estágio: repouso → estresse → resfriamento
   ↓
Amostras CSV a cada ~1 s + logs de processos
   ↓
resumo.json por etapa e por execução
   ↓
Restauração dos limites originais
   ↓
comparar.py → HTML + CSV consolidado
```

## Blocos

`rpi4_fullchip.py` faz toda a orquestração, coleta dados do `/sys/class/thermal`, `/proc/stat`, `/proc/meminfo` e `vcgencmd`, cria processos filhos para estresse e protege a execução.

`gpu_headless_v3d.c` abre render node DRM e cria contexto EGL/OpenGL ES2 com destino FBO/surfaceless quando disponível, renderizando sem monitor físico. Ele confirma `GL_RENDERER: V3D` e contabiliza frames.

`stress-ng` recebe um worker para `cpu_single`, quatro para multicore e um worker de memória `--vm` no cenário combinado; o método de CPU é `matrixprod`.

`comparar.py` lê pastas/ZIPs de uma execução e gera gráficos SVG embutidos em HTML, tabela de resumo, CSV unificado e metadados.

## Limitações metodológicas

A suíte não controla temperatura ambiente, carga exata dos serviços em produção, qualidade da alimentação nem diferenças entre revisões de placa. Os resultados do perfil 2 GB/passivo e 8 GB/torre são **comparações de montagens reais**, não isolamento do dissipador na mesma placa.

A GPU é validada por renderização hardware e frames, mas não é medida em percentual de uso. A telemetria não mede corrente, tensão real em carga ou watts. `0x50000` indica histórico prévio de subtensão/throttling, não ativo nesse instante.
