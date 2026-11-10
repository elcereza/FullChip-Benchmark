# AGENTS.md — FullChip Benchmark

## Contexto e missão

Este repositório implementa uma suíte **específica** de ensaio térmico e de estabilidade para Raspberry Pi 4. Foi desenvolvido com auxílio de IA a partir de requisitos de comparação entre dissipação passiva e uma torre ventilada. Não é um benchmark universal, não mede watts térmicos absolutos e não pretende ocupar cada bloco do BCM2711 a 100% de utilização.

Links de referência:

- [Documentação do projeto](https://elcereza.com/projects/raspberry-pi-4-teste-estresse-cpu-gpu-ram)
- [Resultados térmicos publicados](https://elcereza.com/blog/raspberry-pi-4-dissipacao-ativa-ou-passiva-qual-usar)
- [Repositório oficial](https://github.com/elcereza/FullChip-Benchmark)

## Estrutura de código

- `rpi4_fullchip.py`: coordena pré-flight, GPU V3D, política `cpufreq`, períodos de repouso/carga/resfriamento, amostragem, logs e `resumo.json`.
- `gpu_headless_v3d.c`: renderização por hardware com EGL, OpenGL ES2 e GBM por render node headless.
- `comparar.py`: lê resultados em diretório ou ZIP e gera HTML, CSV e resumos consolidados, somente com bibliotecas padrão Python.
- `testar_2gb_case.sh` e `testar_8gb_torre.sh`: perfis de referência, com parâmetros adicionais encaminhados ao script Python.
- `instalar_dependencias.sh`: exige Raspberry Pi 4 real, instala dependências APT e compila C localmente.
- `diagnostico_rapido.sh` e `diagnostico_frequencia_1500.sh`: inspeção e ensaio pontual de cpufreq.
- `docs/`, `tests/` e `examples/`: documentação, verificação estática e exemplos de saída.

## Regras de segurança inegociáveis

1. **Não desative nem contorne** corte por subtensão, throttling, limite térmico, RAM crítica ou alteração de frequência inesperada.
2. **Nunca introduza overclock ou overvoltage silenciosos** e nunca modifique `/boot/firmware/config.txt` automaticamente.
3. Preserve o snapshot/restauração de `scaling_min_freq` e `scaling_max_freq`. Em caso de exceção ou sinal, tente encerrar processos filhos e restaurar a política.
4. Não apresente `0x50000` como subtensão **ativa**; flags históricas e atuais são distintas.
5. Não valide GPU se `GL_RENDERER` mostrar `llvmpipe`, `softpipe`, `swrast` ou não mostrar V3D; GPU precisa de hardware comprovado e frames gerados.
6. Não trate MHz de V3D como percentual de utilização gráfica, nem temperatura de SoC como medida direta de potência em watts.
7. Não execute ensaios físicos do benchmark automaticamente em ambiente remoto, servidor de produção ou CI. Requer autorização e acompanhamento operacional humanos.
8. Não suba logs de rede/servidores, dumps pessoais, credenciais ou resultados brutos indiscriminadamente para Git.

## Dependências e ambiente

Raspberry Pi 4 Model B, sistema baseado em Debian/Raspberry Pi OS com APT, `sudo`, `python3` (bibliotecas padrão), `stress-ng`, `glmark2-es2-drm`, `build-essential`, `libegl-dev`, `libgles-dev`, `libgbm-dev` e bibliotecas EGL/GLESv2/GBM para compilar `gpu_headless_v3d.c`.

O executável `gpu_headless_v3d` é um **artefato compilado** e **não deve ser versionado**. O CI é estático, não emula um BCM2711 e não comprova suporte gráfico de hardware.

## Contrato de comportamento

- Estágios: `cpu_single`, `cpu_multi`, `gpu_3d`, `cpu_gpu`, `cpu_gpu_ram`.
- Durações normais por estágio: 30 s repouso + 300 s estresse + 180 s resfriamento; com `--smoke`: 3 + 8 + 4 s.
- Frequências permitidas pelo parser: 1500 ou 1800 MHz. Só executar frequência confirmada pelo driver.
- RAM do cenário combinado: um worker `stress-ng --vm 1` com 20% da memória disponível, limitado a 512 MiB, e verificação de espaço mínimo.
- `resumo.json`: documento autoritativo do estado final e restauração do relógio. Cada cenário válido precisa `status=OK`.
- CSV: aproximadamente 1 amostra/s, com fases `repouso`, `stress` e `resfriamento`.
- Scripts de perfil não implicam alteração de serviços já executados no Pi.

## Como validar mudanças

Em máquina de desenvolvimento:

```bash
bash scripts/validar_repositorio.sh
```

Em Raspberry Pi 4, *sob supervisão humana*:

```bash
sudo bash instalar_dependencias.sh
bash diagnostico_rapido.sh
./gpu_headless_v3d --width 640 --height 360 --seconds 3
bash testar_2gb_case.sh --stages gpu_3d --smoke
```

O último comando é específico ao perfil **de 1,5 GHz**. No perfil de 8 GB, usar `bash testar_8gb_torre.sh --freqs 1500 --stages gpu_3d --smoke` e validar a frequência de 1,8 GHz separadamente. Nunca afirme que uma mudança foi testada em hardware real se apenas CI ou testes estáticos passaram.

## Princípios de manutenção

- Mudanças pequenas, reversíveis e compatíveis com o formato de saída.
- Preservar nomes de campos CSV e JSON sempre que possível; se mudar, atualizar comparador, exemplos, documentação e testes.
- Adicionar casos de teste para funções puras (renderer, formatos, validações) antes de alterar caminhos de hardware.
- Distinguir resultados **observados**, **estimativas** e **hipóteses** nas descrições de issues, releases e documentação.
- Não usar resultados de placas distintas para inferir causalidade exclusiva do dissipador sem controlar confusores.
- Atualizar README e docs em português, incluindo comandos reproduzíveis.
- Não usar regras horizontais `---` no README: o usuário prefere separações por títulos.

## Limites conhecidos

`run_period()` coleta em intervalos de aproximadamente 1 s e pode não flagrar eventos breves; estados históricos de `get_throttled` já podem estar marcados antes do ensaio. A carga V3D não é quantificada como percentual; não mede potência nem ambiente automaticamente. Os perfis de 2 GB e 8 GB refletem a configuração experimental, não um limite universal de hardware.
