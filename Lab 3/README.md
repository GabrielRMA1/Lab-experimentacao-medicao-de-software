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

- `src/collectors/repositories.py`: **coleta** (seleção, metadados, releases, commits, workflow runs).
- `src/metricas/lead_time.py`: **cálculo** do Lead Time (RQ 02).
- `src/main.py`: ponto de entrada do pipeline de coleta.
- `tests/`: testes unitários.
- `data/cache/`: espaço reservado para cache/retomada das próximas etapas.

## Lead Time (RQ 02)
 
Regras (definição operacional do enunciado, seção 5/RQ 02):
 
- Entrega = `published_at` da release R. Início = `commit.author.date`.
- **(a) por release:** data de R − commit mais antigo de R; valor do repositório = mediana entre as releases.
- **(b) por commit:** data de R − data de cada commit; valor do repositório = mediana de todos os commits.
- Unidade: **horas**. Também são salvos Q1 e Q3 (para o IQR).
- A primeira release (sem release anterior) não gera intervalo e fica fora.
- Release sem commits válidos: não entra na mediana e é contada em `n_releases_sem_commits`.
- Commit sem data, ou com data posterior à release: ignorado e contado em `n_commits_invalidos`.
- Mesmo `sha` em duas releases: contado só na primeira (`n_commits_duplicados`).
Como rodar (a partir da pasta `Lab 3`, depois da coleta):
 
```powershell
python -m src.metricas.lead_time          # gera data/results/lead_time.csv e .json
pytest --cov=src.metricas --cov-report=term-missing
```
 
A execução salva `data/results/lead_time.csv` e `data/results/lead_time.json`.
 
### Dicionário de dados (`data/results/lead_time.csv`)
 
| Coluna | Unidade | Origem |
|---|---|---|
| `full_name` | texto | dono/repositório |
| `n_releases_avaliadas` | contagem | releases com ao menos 1 commit válido |
| `n_releases_sem_commits` / `n_releases_sem_data` / `n_releases_fora_janela` | contagem | releases descartadas do cálculo, por motivo |
| `n_commits` / `n_commits_invalidos` / `n_commits_duplicados` | contagem | commits usados / ignorados |
| `lead_time_release_mediana_h` (+ `_q1_h`, `_q3_h`) | horas | variante (a) |
| `lead_time_commit_mediana_h` (+ `_q1_h`, `_q3_h`) | horas | variante (b) |
| `coleta_incompleta` | booleano | algum intervalo do cache não terminou de ser coletado |

## Regra importante

O token deve ficar somente na variável de ambiente `GITHUBTOKEN`. Não coloque o token em código, README ou commit.
