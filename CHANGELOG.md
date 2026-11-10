# Histórico de versões

## v1.3 — base para publicação

- Corrigida a gestão temporária dos limites de frequência `cpufreq`, verificando a persistência do teto solicitado e restaurando mínimo/máximo.
- Preservados os cinco estágios CPU, GPU e RAM, com coleta CSV/JSON e parada preventiva.
- Validação headless real da GPU V3D por EGL/GBM, sem depender de HDMI.
- Instalador que compila o binário gráfico localmente no Raspberry Pi 4.
- Adicionada organização pública: README detalhado, `AGENTS.md`, documentação técnica, testes estáticos e CI.

Consulte o [blog dos resultados](https://elcereza.com/blog/raspberry-pi-4-dissipacao-ativa-ou-passiva-qual-usar) e a [página do projeto](https://elcereza.com/projects/raspberry-pi-4-teste-estresse-cpu-gpu-ram).
