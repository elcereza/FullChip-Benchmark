# Publicação do projeto no GitHub

Repositório já criado: **[elcereza/FullChip-Benchmark](https://github.com/elcereza/FullChip-Benchmark)**, branch padrão `main`. No estado consultado em 9/11/2026, contém `README.md` inicial e `LICENSE` MIT. O pacote preparado inclui uma cópia coerente dessa licença.

## Método recomendado: substituir o conteúdo inicial sem apagar o histórico remoto

No computador onde você preparará o commit, instale Git e clone o repositório existente:

```bash
git clone https://github.com/elcereza/FullChip-Benchmark.git
cd FullChip-Benchmark
```

**Extraia o ZIP de entrega em outra pasta**. Copie os arquivos e diretórios do pacote para dentro do clone existente, substituindo o README antigo e preservando `.git/`:

```bash
# Exemplo: depois de extrair o ZIP na pasta Downloads
cp -a ~/Downloads/FullChip-Benchmark_GitHub_Ready/. ./
```

Ajuste o caminho ao local onde descompactou o ZIP. O comando copia arquivos ocultos como `.gitignore` e `.github/`, mas **não** apaga o diretório `.git` do clone, pois o pacote não inclui `.git/`.

Verifique antes de publicar:

```bash
bash scripts/validar_repositorio.sh
git status --short
git diff -- README.md LICENSE
git check-ignore gpu_headless_v3d
```

`git check-ignore gpu_headless_v3d` deve confirmar que o executável compilado seria ignorado. Não deve haver CSVs pessoais nem logs extensos no `git status`.

Crie um commit e envie:

```bash
git add README.md AGENTS.md CONTRIBUTING.md SECURITY.md CHANGELOG.md LICENSE   .gitignore .gitattributes .editorconfig .github docs examples tests scripts   rpi4_fullchip.py comparar.py gpu_headless_v3d.c   instalar_dependencias.sh diagnostico_rapido.sh   diagnostico_frequencia_1500.sh testar_2gb_case.sh testar_8gb_torre.sh

git commit -m "docs: publica FullChip Benchmark v1.3 com instalacao e diagnosticos"
git push origin main
```

Se o GitHub solicitar autenticação, utilize Git Credential Manager, SSH ou um token pessoal de escopo apropriado. Não cole tokens em comandos publicados, arquivos do repositório ou mensagens de suporte.

## Conferência pós-publicação

Abra [o README](https://github.com/elcereza/FullChip-Benchmark) e confirme que links internos, `AGENTS.md` e comandos estão corretos. Em um Raspberry Pi 4, clone em diretório novo e faça instalação, diagnóstico V3D e smoke test antes de afirmar que a distribuição pública está validada.

Não faça `git push --force` para substituir a branch remota e não apague a licença do repositório existente.
