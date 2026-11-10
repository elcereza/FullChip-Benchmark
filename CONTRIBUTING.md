# Contribuindo com o FullChip Benchmark

Este projeto prioriza documentação clara, segurança operacional e repetibilidade dos ensaios. Contribuições são bem-vindas, desde que descrevam **o problema real, as mudanças propostas, como foram validadas e seus limites**.

Antes de alterar código, leia [AGENTS.md](AGENTS.md) e [Arquitetura](docs/ARQUITETURA.md). Abra um issue ou pull request com descrição do comportamento observado, modelo e revisão do Raspberry Pi, versão do kernel, configuração `cpufreq`, dependências e logs sanitizados.

Rode `bash scripts/validar_repositorio.sh`; se a mudança afeta GPU, frequência ou estresse, acrescente os resultados de smoke tests físicos supervisionados. Não é necessário publicar seus CSVs completos se contiverem dados pessoais ou caminhos internos.

Nunca desabilite proteções para tentar fazer um teste passar. Regras de formatação: Python sem dependências pip, scripts Bash com `set -euo pipefail` quando apropriado, comentários concisos e documentação em português.
