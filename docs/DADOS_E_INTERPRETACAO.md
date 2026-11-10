# Saídas e interpretação

## Pasta e ciclo

Cada execução cria uma pasta única sob `~/rpi4-fullchip-results/`. Há arquivos CSV por estágio/frequência, logs de CPU/GPU, `gpu_preflight.log` e `resumo.json`. O tempo interno reinicia em cada fase, então a coluna `elapsed_s` precisa ser interpretada junto com `phase`.

## Principais colunas CSV

- `timestamp_iso` / `unix_s`: tempo real do evento.
- `elapsed_s`: segundos transcorridos na fase.
- `freq_target_mhz`: limite de CPU solicitado no ensaio.
- `stage` / `phase`: tipo de carga e uma das fases (`repouso`, `stress`, `resfriamento`).
- `temperature_c`: temperatura do sensor do SoC.
- `cpu_util_pct`: utilização agregada da CPU derivada de `/proc/stat`.
- `cpu_freq_mhz`: leitura instantânea de clock ARM.
- `gpu_v3d_clock_mhz`: clock V3D, **não percentual de ocupação da GPU**.
- `throttled_hex`: máscara hexadecimal devolvida pelo firmware.
- `undervoltage_now`, `freq_capped_now`, `throttling_now`, `softtemp_now`: bits ativos no instante da amostra.
- `undervoltage_ever`, `throttling_ever`: histórico desde o boot.
- `mem_available_mib`: memória disponível estimada pelo sistema.
- `stress_process_alive`, `gpu_process_alive`: processos de carga em execução no momento do registro.

## Interpretação e comparabilidade

Não confunda temperatura máxima com capacidade de dissipação em watts. Para inferência térmica são necessários, no mínimo, controles de potência, ambiente, montagem e regime estacionário. A diferença entre duas curvas pode ser influenciada pela carga de fundo, revisões de hardware, temperatura do ambiente, pasta térmica e ventilação.

Se a máscara histórica já estava ativada antes do teste, uma nova queda muito curta pode ocorrer entre duas amostras e não produzir uma nova alteração persistente distinguível na sequência CSV.

`resumo.json` é a principal fonte para o estado final de cada cenário: `OK` e `NAO_EXECUTADO` não são equivalentes. Para GPU, confira `gpu_preflight.log` e logs por estágio.

Os arquivos em `examples/` são resultados observados no ensaio original, **não uma validação para novos ambientes**.
