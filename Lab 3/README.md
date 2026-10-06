# Lab 03 — Mineração de Métricas DORA

Base inicial da S01 do Laboratório de Experimentação de Software.

## Requisitos

- Python 3.11+
- Token do GitHub com acesso à API REST.

## Configuração

No PowerShell:

```powershell
$env:GITHUBTOKEN="SEU_TOKEN_AQUI"
```

Opcionalmente, altere a consulta de repositórios:

```powershell
$env:GITHUB_REPO_QUERY="stars:>1000"
```

O alvo da amostra final da S01 é 100. Ele pode ser ajustado separadamente da
quantidade de candidatos buscados:

```powershell
$env:S01_SAMPLE_TARGET="100"
```

A janela de observação é configurada por `OBSERVATION_START` e
`OBSERVATION_END` no arquivo `.env`. Os valores atualmente configurados são
**PROVISÓRIOS** (12 meses anteriores ao lançamento do Lab 3) e devem ser
substituídos quando o professor publicar as datas oficiais:

```dotenv
OBSERVATION_START=2025-10-02T00:00:00Z
OBSERVATION_END=2026-10-02T23:59:59Z
```

Os valores são lidos do `.env`, não fixados no código. A janela inclusiva é
aplicada a `published_at` das releases, `commit.author.date` dos commits e
`created_at` dos workflow runs. Releases válidas continuam sendo apenas as
que têm `draft=false` e `prerelease=false`; workflow runs válidos são da
branch padrão e do evento `push`. A amostra final da S01 não representa a
meta mínima de 300 repositórios da S02.

## Instalação

```powershell
pip install -r requirements.txt
```

## Execução

A partir da pasta `Lab 3`:

```powershell
python src/main.py
```

A execução salva:

- `data/repositories.json`: repositórios da amostra final da S01;
- `data/funnel.json`: etapas do funil.

## Estrutura

- `src/collectors/repositories.py`: seleção e metadados dos repositórios.
- `src/main.py`: ponto de entrada do pipeline.
- `tests/`: testes unitários.
- `data/cache/`: espaço reservado para cache/retomada das próximas etapas.

## Regra importante

O token deve ficar somente na variável de ambiente `GITHUBTOKEN`. Não coloque o token em código, README ou commit.
