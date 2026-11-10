# FullChip Benchmark

**Teste de estresse térmico de CPU, GPU V3D e RAM para Raspberry Pi 4.** Uma ferramenta criada para comparar o comportamento de diferentes montagens de dissipação, observando aquecimento, resfriamento, frequência e possíveis limitações de desempenho.

O projeto nasceu de uma necessidade concreta: verificar se o Raspberry Pi 4 conseguia permanecer estável sob carga computacional intensiva sem depender de incidentes em produção ou de criar várias aplicações artificiais ao mesmo tempo. A ferramenta aplica uma sequência de cargas controladas, registra telemetria e interrompe os ensaios quando encontra condições que prejudicam a segurança ou a validade da comparação.

**Leia sobre o projeto:** [Como funciona o FullChip Benchmark na Elcereza](https://elcereza.com/projects/raspberry-pi-4-teste-estresse-cpu-gpu-ram).

**Veja os resultados experimentais:** [Raspberry Pi 4: dissipação ativa ou passiva, qual usar?](https://elcereza.com/blog/raspberry-pi-4-dissipacao-ativa-ou-passiva-qual-usar).

Este README descreve o processo completo de instalação e utilização. O programa não é um benchmark universal de desempenho, não substitui ferramentas consolidadas e não mede a potência térmica absoluta em watts. Foi desenvolvido com auxílio de IA a partir de requisitos específicos, e seu comportamento deve ser verificado em cada ambiente.

## Sumário

1. [O que este projeto faz](#1-o-que-este-projeto-faz)
2. [Hardware e compatibilidade](#2-hardware-e-compatibilidade)
3. [Arquitetura e cenários](#3-arquitetura-e-cenários)
4. [Cuidados antes de instalar](#4-cuidados-antes-de-instalar)
5. [Clonagem e instalação](#5-clonagem-e-instalação)
6. [Primeiro diagnóstico](#6-primeiro-diagnóstico)
7. [Validação da GPU V3D sem monitor](#7-validação-da-gpu-v3d-sem-monitor)
8. [Teste rápido de segurança](#8-teste-rápido-de-segurança)
9. [Bateria completa](#9-bateria-completa)
10. [Parâmetros e execução personalizada](#10-parâmetros-e-execução-personalizada)
11. [Como os resultados são salvos](#11-como-os-resultados-são-salvos)
12. [Comparação e interpretação](#12-comparação-e-interpretação)
13. [Subtensão e throttling](#13-subtensão-e-throttling)
14. [Problemas frequentes](#14-problemas-frequentes)
15. [Estrutura do repositório](#15-estrutura-do-repositório)
16. [Desenvolvimento, contribuição e licença](#16-desenvolvimento-contribuição-e-licença)

## 1. O que este projeto faz

A suíte organiza cinco cenários independentes, cada um com **30 segundos de repouso**, **300 segundos de carga** e **180 segundos de resfriamento**. A coleta ocorre aproximadamente uma vez por segundo, com campos como temperatura do SoC, uso da CPU, clock ARM, clock V3D, memória disponível e indicadores de subtensão ou throttling.

| Estágio | CPU | GPU | RAM | Objetivo |
|:--|:--|:--|:--|:--|
| `cpu_single` | 1 trabalhador | Sem carga gráfica criada pelo benchmark | Uso normal | Identificar a resposta térmica de carga em um núcleo |
| `cpu_multi` | 4 trabalhadores | Sem carga gráfica criada pelo benchmark | Uso normal | Exigir os quatro núcleos Cortex-A72 |
| `gpu_3d` | Sem carga intensa de CPU criada pelo benchmark | Renderização V3D | Uso normal | Verificar o comportamento da GPU real sem HDMI |
| `cpu_gpu` | 4 trabalhadores | Renderização V3D | Uso normal | Combinar computação ARM e gráfica |
| `cpu_gpu_ram` | 4 trabalhadores | Renderização V3D | Alocação controlada de memória | Aplicar o cenário misto mais abrangente |

Na CPU, a ferramenta usa [`stress-ng`](https://manpages.debian.org/stress-ng) com o método `matrixprod`. Na GPU, utiliza um utilitário escrito em C que abre EGL/GBM por `/dev/dri/renderD*` e verifica `GL_RENDERER`, recusando renderização por software. A GPU tem uma arquitetura própria; não é correto tratar seus recursos como quatro núcleos ARM adicionais.

**Importante:** quatro trabalhadores pressionam os quatro núcleos físicos disponíveis, mas a taxa real de processamento depende da frequência, da temperatura, dos serviços existentes e do escalonador Linux. A telemetria não quantifica o uso percentual do bloco V3D, apenas valida renderização por hardware e registra sinais auxiliares.

## 2. Hardware e compatibilidade

A suíte foi preparada para **Raspberry Pi 4 Model B**, com SoC BCM2711 (quatro núcleos ARM Cortex-A72 e GPU VideoCore VI/V3D). A família possui diferentes versões de memória e revisões de placa. **O pacote foi efetivamente testado em duas placas específicas**, e isso não equivale a validação em toda combinação possível de hardware e sistema:

| Perfil observado | Placa | RAM | Frequências utilizadas | Refrigeração |
|:--|:--|:--|:--|:--|
| Laboratório | Pi 4 Rev 1.1 | 2 GB | 1.500 MHz | Case de alumínio passivo |
| Servidor | Pi 4 Rev 1.4 | 8 GB | 1.500 e 1.800 MHz | Torre com heat pipes e fan |

As frequências são escolhidas conforme o que o driver `cpufreq` e a configuração da placa permitem. **A RAM não determina sozinha o clock disponível.** Este projeto não faz overclock, não altera a tensão do SoC e não edita o arquivo de boot.

Ambientes do ensaio original: distribuições Raspberry Pi OS/Debian baseadas em Bookworm e Trixie, executadas em placas Pi 4 reais. O instalador usa `apt`, portanto pressupõe uma distribuição compatível com APT e acesso aos repositórios.

## 3. Arquitetura e cenários

O fluxo é: verificação da placa e dependências → validação curta da GPU → ajuste temporário de limite de frequência → repouso → estresse → resfriamento → registro CSV/JSON → restauração dos limites originais.

Cada fase gera amostras próprias. Isso permite comparar **a evolução térmica no tempo**, não apenas o maior valor atingido. Os cenários GPU só podem ser aceitos quando a saída do renderizador comprova uso do V3D. Se o hardware gráfico não for confirmado, esses cenários são explicitamente ignorados.

O ciclo completo de cinco cenários em uma frequência soma **42 minutos e 30 segundos** de fases, fora preparação e validações. No perfil de 8 GB, as dez etapas em duas frequências somam **85 minutos de fases**, mais a preparação. Não execute outra cópia em paralelo.

Consulte a explicação das decisões técnicas em [Arquitetura e telemetria](docs/ARQUITETURA.md).

## 4. Cuidados antes de instalar

**Não execute estresse em produção sem janela de manutenção.** Mesmo com proteções, CPU e GPU podem ficar ocupadas por minutos, afetando serviços, NAS, bancos de dados, sincronização de arquivos e dispositivos conectados.

Antes de iniciar, confirme fonte e cabo adequados (a recomendação típica do Pi 4 é 5,1 V / 3 A), ventilação, espaço de armazenamento e ausência de interrupções críticas. Registros históricos de subtensão devem ser investigados, principalmente se houver periféricos USB conectados. Não remova adaptadores seriais de um laboratório sem avaliar seu impacto.

O monitor faz parada preventiva quando encontra, por exemplo, temperatura de **78 °C** (padrão alterável entre 65 e 80 °C), subtensão ativa, throttling ativo, memória disponível abaixo de 128 MiB ou alteração inesperada do limite de frequência. Essas proteções **não garantem ausência de dano ou corrupção**; eventos rápidos entre amostras podem não ser observados. Reinicializações abruptas também podem impedir restauração do clock no processo de limpeza.

## 5. Clonagem e instalação

No terminal do Raspberry Pi 4, instale o Git (caso ainda não exista):

```bash
sudo apt update
sudo apt install -y git
```

Clone o repositório oficial:

```bash
git clone https://github.com/elcereza/FullChip-Benchmark.git
cd FullChip-Benchmark
```

Confira o conteúdo esperado:

```bash
ls -la
```

Você deve encontrar `rpi4_fullchip.py`, `comparar.py`, `gpu_headless_v3d.c`, os dois scripts de perfil, os diagnósticos e o instalador. Prepare as dependências:

```bash
sudo bash instalar_dependencias.sh
```

O instalador executa `apt-get update`, instala `stress-ng`, `glmark2-es2-drm`, `build-essential`, `libegl-dev`, `libgles-dev` e `libgbm-dev`. Depois compila `gpu_headless_v3d.c` **no próprio Raspberry Pi**, criando o executável `gpu_headless_v3d` localmente. O binário não é versionado no Git para evitar incompatibilidades entre máquinas.

**O instalador altera pacotes do sistema**, mas não reconfigura serviços, governor, voltagem ou boot. Não execute `apt autoremove` indiscriminadamente em um servidor.

Confira os programas instalados:

```bash
command -v stress-ng
ls -l ./gpu_headless_v3d
python3 --version
```

## 6. Primeiro diagnóstico

Execute:

```bash
bash diagnostico_rapido.sh
```

Ele lê modelo, versão do kernel, política `cpufreq`, flags `get_throttled`, dispositivos DRM e tenta uma pequena renderização de cerca de 3 segundos, se o executável de GPU existir. Este passo **não** equivale à bateria de estresse.

Para conferir diretamente a política de frequência:

```bash
P=/sys/devices/system/cpu/cpufreq/policy0
for f in cpuinfo_max_freq scaling_min_freq scaling_max_freq scaling_governor; do
  printf '%s: ' "$f"
  cat "$P/$f"
done
vcgencmd get_throttled
vcgencmd measure_temp
```

**Não confunda** `scaling_cur_freq` com `scaling_max_freq`: o primeiro é a frequência instantânea (pode cair por baixa demanda); o segundo é o teto atual aplicado pelo driver.

## 7. Validação da GPU V3D sem monitor

Um Raspberry usado via SSH pode não ter um conector DRM ativo. Portanto, a primeira abordagem convencional baseada em `glmark2-es2-drm` pode falhar com `Failed to find a suitable connector` mesmo quando a GPU está funcionando.

A solução é um renderizador headless via EGL/GBM:

```bash
./gpu_headless_v3d --width 640 --height 360 --seconds 3
```

A execução válida deve apresentar algo semelhante a:

```text
GL_RENDERER: V3D 4.2.14.0
GPU_DRAW_FRAMES: 121
```

Os números variam de acordo com ambiente e versão do Mesa. **O requisito é `V3D` no renderizador e uma contagem positiva de quadros**, não exatamente os valores do exemplo.

Se aparecer `llvmpipe`, `softpipe`, `swrast`, erro de EGL/GBM ou ausência de `/dev/dri/renderD*`, não considere o teste de GPU validado. Consulte [Diagnóstico de problemas](docs/PROBLEMAS_COMUNS.md) antes de iniciar qualquer teste longo.

## 8. Teste rápido de segurança

Depois de validar a GPU, faça um **smoke test** de somente um estágio, com 3 segundos de repouso, 8 de carga e 4 de resfriamento. Isso verifica a cadeia de coleta, o acionamento do workload e as proteções sem partir diretamente para os cinco minutos.

No Pi 4 do laboratório (perfil de 2 GB, até 1,5 GHz):

```bash
bash testar_2gb_case.sh --stages gpu_3d --smoke
```

No Pi 4 do servidor (perfil de 8 GB, primeiro a 1,5 GHz):

```bash
bash testar_8gb_torre.sh --freqs 1500 --stages gpu_3d --smoke
```

Confira ao final o status do cenário, o relatório `resumo.json`, o `gpu_preflight.log` e o CSV. O resultado esperado do cenário é `OK`; `NAO_EXECUTADO` não equivale a sucesso.

Também é possível validar um pequeno estresse combinado, mas **não insistir** se surgir subtensão:

```bash
bash testar_2gb_case.sh --stages cpu_gpu --smoke
bash testar_8gb_torre.sh --freqs 1500 --stages cpu_gpu --smoke
```

As linhas acima são **alternativas para cada placa**, não duas execuções para o mesmo Raspberry. Se houver subtensão, pare e revise alimentação antes de avançar.

## 9. Bateria completa

No Raspberry Pi de 2 GB com dissipador passivo, depois do smoke test e de conferir a alimentação:

```bash
bash testar_2gb_case.sh
```

O script solicita os cinco cenários a 1,5 GHz. Se o driver não permitir esse teto, o perfil será rejeitado; o script não força uma frequência indisponível.

No Raspberry Pi de 8 GB com torre ventilada:

```bash
sudo bash diagnostico_frequencia_1500.sh
bash testar_8gb_torre.sh
```

O diagnóstico testa temporariamente a transição para 1,5 GHz e busca restaurar os limites originais. O segundo comando solicita cinco estágios a 1,5 GHz e depois os cinco mesmos estágios a 1,8 GHz. **1,8 GHz só será testado se o driver e a placa permitirem.**

É normal a frequência instantânea cair para aproximadamente 600 MHz entre fases por causa do governor. O teste considera o teto configurado, não presume frequência fixa durante repouso.

No final, confira no terminal:

```text
STATUS: CONCLUIDO
CPU max original restaurado: True
```

Verifique também o `resumo.json`, porque um processo pode concluir a execução com estágio não executado ou interrompido. O script tenta restaurar os limites originais inclusive após interrupção controlada; **se a máquina desligar abruptamente, confirme o estado após a retomada**.

## 10. Parâmetros e execução personalizada

Os dois scripts de perfil aceitam parâmetros adicionais enviados ao programa principal. Para conhecer todos:

```bash
python3 rpi4_fullchip.py --help
```

Os argumentos relevantes são:

| Parâmetro | Função | Padrão |
|:--|:--|:--|
| `--stages` | Executa um ou mais dos cinco cenários, separados por vírgula | Todos |
| `--freqs` | Frequências-alvo permitidas: 1500 e/ou 1800 MHz | Definidas no script de perfil |
| `--smoke` | Teste rápido de 3+8+4 segundos | Desativado |
| `--rest-sec` | Segundos de repouso | 30 |
| `--stress-sec` | Segundos de carga | 300 |
| `--cool-sec` | Segundos de resfriamento | 180 |
| `--temp-stop` | Limite preventivo (65 a 80 °C) | 78 °C |
| `--gpu-width`, `--gpu-height` | Resolução do renderizador 3D | 1280 × 720 |
| `--ambient-c` | Temperatura ambiente informada manualmente para metadados | Não informada |
| `--output` | Diretório-base de resultados | Diretório de resultados no HOME do usuário |
| `--dry-run` | Verifica pré-requisitos sem alterar clock | Desativado |

Exemplos:

```bash
# Apenas CPU multicore, com teste curto
bash testar_2gb_case.sh --stages cpu_multi --smoke

# GPU e CPU + GPU a 1,5 GHz no servidor
bash testar_8gb_torre.sh --freqs 1500 --stages gpu_3d,cpu_gpu

# Reduzir a duração do ensaio de CPU (não equivale ao protocolo experimental original)
bash testar_2gb_case.sh --stages cpu_single --rest-sec 15 --stress-sec 60 --cool-sec 60

# Verificar pré-requisitos (sem executar a carga)
sudo python3 rpi4_fullchip.py --label diagnostico --freqs 1500 --dry-run
```

Se alterar frequência, duração, resolução ou carga de memória, **não compare os resultados como se fossem protocolos idênticos**. O uso de `--stages` filtra cenários; não significa que o restante será executado automaticamente mais tarde.

## 11. Como os resultados são salvos

Por padrão, a ferramenta grava os resultados em:

```text
/home/SEU_USUARIO/rpi4-fullchip-results/
└── AAAAMMDDTHHMMSSZ_identificador_do_dispositivo/
    ├── resumo.json
    ├── gpu_preflight.log
    ├── 1500MHz_cpu_single_amostras_1s.csv
    ├── 1500MHz_cpu_single_stress.log
    ├── 1500MHz_gpu_3d_amostras_1s.csv
    └── ... demais cenários executados
```

`resumo.json` registra ambiente, configuração, cenários, estatísticas, eventos de proteção e tentativa de restauração do clock. Os CSVs trazem dados temporais de cada fase; os logs descrevem o comportamento dos utilitários de estresse.

**Nunca trate `throttled=0x50000` como evento ativo por si só.** Os bits de histórico continuam registrados desde a inicialização, enquanto os bits baixos indicam condições atuais no momento da amostra. Veja [Telemetria e dados](docs/DADOS_E_INTERPRETACAO.md).

Para compartilhar os resultados, entre no diretório-pai e compacte a pasta de uma execução:

```bash
cd ~/rpi4-fullchip-results
zip -r ensaio_pi4.zip AAAAMMDDTHHMMSSZ_identificador_do_dispositivo
```

Substitua o nome de exemplo pelo diretório real mostrado em `RESULTADOS:`. Não inclua logs de infraestrutura, credenciais ou arquivos pessoais no ZIP.

## 12. Comparação e interpretação

Com dois diretórios ou dois ZIPs de resultados, execute o comparador sem precisar de pacotes Python adicionais:

```bash
python3 comparar.py /caminho/resultado_2gb.zip /caminho/resultado_8gb.zip --out comparacao
```

Abra `comparacao/comparativo.html` no navegador. Também são gerados `amostras_unificadas.csv` e `resumos_originais.json`.

O HTML mostra as cinco curvas de temperatura e a tabela por estágio/frequência. Compare especialmente **temperatura inicial**, **pico**, **elevação relativa ao repouso**, **inclinação durante carga**, **resfriamento**, **frequência real**, **CPU ocupada** e **eventos de proteção**.

O estudo que motivou a ferramenta pode ser consultado no [blog da Elcereza](https://elcereza.com/blog/raspberry-pi-4-dissipacao-ativa-ou-passiva-qual-usar). Nele, as duas montagens foram analisadas sob frequências e perfis comparáveis.

**Limite metodológico:** o script não mede watts elétricos nem térmicos e não tem medidor de temperatura ambiente integrado. Por isso, diferenças térmicas não comprovam, isoladamente, quantos watts cada dissipador removeu. Como são placas diferentes, firmware, revisão, alimentação e temperatura inicial também influenciam a comparação.

## 13. Subtensão e throttling

A leitura principal é:

```bash
vcgencmd get_throttled
```

| Código | Interpretação resumida |
|:--|:--|
| `0x0` | Sem flags ativas ou históricas registradas |
| `0x5` | Subtensão ativa e throttling ativo |
| `0x50000` | Subtensão e throttling ocorreram anteriormente, não necessariamente agora |
| `0x50005` | Eventos históricos e condições ativas |

A ferramenta interrompe a carga se detectar subtensão ativa, throttling ativo ou alterações inesperadas no teto de clock. A queda de frequência em repouso, isoladamente, não é throttling: pode ser comportamento normal de economia de energia.

Para investigar novos eventos do kernel:

```bash
sudo journalctl -k -b --no-pager | grep -Ei 'under.?voltage|voltage normalised|throttl'
```

Se houver eventos de alimentação, revise fonte, cabo, hub USB e conexões antes de insistir em CPU + GPU. Desconectar periféricos do laboratório pode interferir em serviços e testes em andamento.

## 14. Problemas frequentes

**`Failed to find a suitable connector`:** o DRM pode não ter monitor ativo, mesmo com GPU válida. Use o backend EGL/GBM headless e confira `GL_RENDERER`.

**`GL_RENDERER` não contém `V3D`:** teste gráfico não confirmado; não considere resultados GPU válidos.

**`scaling_max_freq` não permanece em 1,5 GHz:** outro serviço ou o driver pode estar rejeitando a alteração; inspecione as políticas de CPU e o diagnóstico, não force overclock.

**`throttled=0x50000`:** histórico registrado, não uma condição ativa automática; confira logs do kernel para eventos novos.

**Benchmark interrompido por subtensão:** proteções atuaram corretamente; investigue alimentação antes de repetir cargas combinadas.

**Sem permissão ou falta de dependências:** execute a instalação com `sudo`, confira `stress-ng` e rode o teste do renderizador no próprio Pi 4.

Para sintomas e verificações mais completas, leia [Problemas frequentes](docs/PROBLEMAS_COMUNS.md).

## 15. Estrutura do repositório

```text
FullChip-Benchmark/
├── README.md                         Documentação principal e instalação
├── AGENTS.md                         Orientações técnicas para agentes de IA
├── rpi4_fullchip.py                  Coordenador do benchmark
├── gpu_headless_v3d.c                Renderizador EGL/GBM em C
├── comparar.py                       Comparador CSV/JSON/HTML
├── instalar_dependencias.sh          Instala dependências e compila GPU
├── diagnostico_rapido.sh             Confere hardware e renderização
├── diagnostico_frequencia_1500.sh    Verifica limites de cpufreq
├── testar_2gb_case.sh                Perfil de laboratório a 1,5 GHz
├── testar_8gb_torre.sh               Perfil do servidor em 1,5 e 1,8 GHz
├── docs/                              Instalação, arquitetura e diagnóstico
├── tests/                             Verificações estáticas e unitárias
├── examples/                          Amostras documentais sem arquivos gigantes
├── .github/workflows/                 Validação estática no GitHub Actions
├── .gitignore
├── CONTRIBUTING.md
└── LICENSE
```

O binário `gpu_headless_v3d` é compilado durante a instalação. Os arquivos de resultado de uma execução não são parte do código-fonte do repositório.

## 16. Desenvolvimento, contribuição e licença

A base foi desenvolvida para um **problema específico de comparação térmica**, com auxílio de IA e revisões a partir dos logs de execução em Raspberry Pi 4 reais. Melhorias devem preservar: segurança elétrica/térmica, validação explícita de GPU V3D, restauração de `cpufreq`, saída estruturada e compatibilidade dos cinco cenários.

Antes de enviar mudanças, rode:

```bash
bash scripts/validar_repositorio.sh
```

Em máquina não Raspberry Pi, essa verificação valida sintaxe e testes de funções puras, **sem simular uma validação física do hardware**. Em Raspberry Pi, siga também o diagnóstico e os smoke tests. Leia [AGENTS.md](AGENTS.md) e [CONTRIBUTING.md](CONTRIBUTING.md) para conhecer as diretrizes de manutenção.

O repositório usa **licença MIT**, conforme o arquivo `LICENSE` já existente no GitHub. O software é fornecido sem garantias: execute ensaios de estresse por sua própria conta e com supervisão adequada.

Para estudar a lógica e o experimento completo, veja a [página do projeto](https://elcereza.com/projects/raspberry-pi-4-teste-estresse-cpu-gpu-ram) e os [resultados térmicos do blog](https://elcereza.com/blog/raspberry-pi-4-dissipacao-ativa-ou-passiva-qual-usar).
