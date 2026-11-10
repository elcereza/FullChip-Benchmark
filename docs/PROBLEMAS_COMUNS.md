# Problemas frequentes e diagnóstico

## GPU não funciona via SSH

Erro como `Failed to find a suitable connector` pode ocorrer com `glmark2-es2-drm` sem monitor conectado. Use `./gpu_headless_v3d --width 640 --height 360 --seconds 3` e exija `GL_RENDERER: V3D` e `GPU_DRAW_FRAMES` positivo. Se renderizar via `llvmpipe`, é software, não GPU real.

## Biblioteca EGL, GBM ou OpenGL ES não encontrada

Reexecute `sudo bash instalar_dependencias.sh` depois de confirmar se os pacotes APT para sua versão de Debian/Raspberry Pi OS estão disponíveis. Não tente baixar bibliotecas aleatórias de sites não oficiais.

## GPU não aparece em /dev/dri

Confira `ls -l /dev/dri/`, `lsmod | grep -E '^(v3d|vc4)'` e versões de kernel/firmware. Não remova módulos DRM de um servidor em produção para tentar corrigir o teste sem planejamento.

## Erro de frequência cpufreq

Compare `cpuinfo_max_freq`, `scaling_min_freq`, `scaling_max_freq` e `scaling_governor` em `/sys/devices/system/cpu/cpufreq/policy0`. O Raspberry pode ter teto de 1,5 GHz por revisão/firmware; **não aumente voltagem ou edite config.txt para forçar 1,8 GHz**. No modelo de 8 GB, rode `sudo bash diagnostico_frequencia_1500.sh` antes da bateria completa.

## Subtensão ou throttling ativo

Pare cargas combinadas se houver `0x5` / `0x50005`. Inspecione fonte, cabo USB-C, contatos e periféricos; o fato de adaptadores USB estarem em standby não elimina a possibilidade de queda de tensão sob carga. Registre logs de kernel próximos ao horário do evento.

## 0x50000 mesmo após o resfriamento

Os bits altos são **histórico desde o boot** e não somem imediatamente após estabilização. Reboot apenas para limpar histórico não é necessário e pode afetar serviços.

## Benchmark interrompido com temperaturas baixas

A causa pode ser **elétrica**, falta de RAM ou alteração de frequência; não atribua automaticamente o evento ao sistema de dissipação.

## Resultados com status NAO_EXECUTADO

A suíte não fabrica dados quando a GPU não está validada ou o clock não pôde ser aplicado. Confira a razão no `resumo.json` antes de fazer gráficos ou conclusões.

## `comparar.py` não abre um ZIP

O ZIP deve conter exatamente um `resumo.json` de uma execução, mais os CSVs referidos nesse resumo. O ZIP original de **código-fonte** não é um arquivo de resultados.
