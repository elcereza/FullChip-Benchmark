# Segurança e riscos operacionais

Esta aplicação aplica carga intensiva ao Raspberry Pi 4. Use supervisão adequada; tenha backups dos dados e janela de manutenção se o sistema executa serviços importantes.

O monitor implementa parada preventiva, mas **não garante** ausência de danos ou corrupção: problemas de fonte e cabo, picos entre amostras, falhas do kernel, interrupções de energia e processos de terceiros são fatores externos à suíte.

**A suíte não foi desenvolvida para fazer overclock**, nem para desativar proteções do firmware. Não remova verificações de subtensão, throttling e temperatura para obter números melhores.

Não anexe tokens de GitHub, arquivos de configuração confidenciais ou logs de produção contendo dados pessoais a issues. Se identificar vulnerabilidade de segurança, use os canais privados disponibilizados pelo mantenedor do repositório antes de divulgação pública.
