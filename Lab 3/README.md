# Lab 03 — Mineração de métricas DORA

Pipeline reprodutível que calcula as métricas DORA (deployment frequency, lead
time, change failure rate e tempo de recuperação) para repositórios populares
do GitHub que usam GitHub Actions. Estado atual: **Sprint 02** (amostra
completa ≥ 300 repositórios, dataset, validação manual).

> Tudo roda a partir da pasta `Lab 3`. O token **nunca** é commitado.

## Requisitos e instalação

- Python 3.11+
- Token do GitHub (REST). Cada integrante usa o **próprio** token (a cota é por token).

```bash
pip install -r requirements.txt
```

Crie um arquivo `.env` (já está no `.gitignore`) — ou exporte as variáveis:

```dotenv
GITHUBTOKEN=ghp_xxx                       # ou GITHUB_TOKEN
OBSERVATION_START=2025-10-02T00:00:00Z    # PROVISÓRIO: troque pelas datas oficiais
OBSERVATION_END=2026-10-02T23:59:59Z
```

**Os três integrantes precisam usar exatamente a mesma janela.** Outras
variáveis (todas opcionais): `GITHUB_REPO_QUERY` (padrão `stars:>1000`),
`CANDIDATES_TARGET` (1500), `SAMPLE_TARGET` (teto da amostra, 400),
`MIN_SAMPLE` (300), `WORKERS` (4), `HEURISTICA_VERSAO`.

## Como rodar (Sprint 02)

```bash
python -m src.pipeline search                  # 1) candidatos -> data/candidates.json (commitar)
python -m src.pipeline collect --shard 1/3     # 2) coleta (cada integrante uma fatia: 1/3, 2/3, 3/3)
python -m src.pipeline merge-cache PASTA...    # 3) junta os data/cache das outras máquinas
python -m src.pipeline consolidate             # 4) funil + dataset + dicionário
python -m src.pipeline amostra-ouro            # 5) sorteia 60 repos e gera o material de rotulagem
#    ... cada integrante rotula sozinho (tools/rotulador.html) ...
python -m src.pipeline concordancia            # 6) kappa de Fleiss + consenso (--parcial se incompleto)
python -m src.pipeline heuristica              # 7) precisão/recall/F1 de cada versão da heurística
python -m src.pipeline consolidate             # 8) refaz o dataset com a heurística escolhida
```

`python -m src.pipeline all` executa 1 → 2 → 4 em uma máquina só.

**Cache e retomada.** Toda resposta da API é gravada por página em
`data/cache/<dono>__<repo>.json`. Se a coleta cair (rate limit, rede,
`Ctrl+C`), rode o mesmo comando de novo: ele continua de onde parou, sem
repetir chamadas. O rate limit é lido de `X-RateLimit-*` (espera automática);
limites secundários usam `Retry-After`; erros 5xx têm *backoff* exponencial.

**Coleta em paralelo (3 tokens).** `--shard I/N` divide os candidatos
(ordenados por estrelas) entre as máquinas; cada fatia para ao atingir sua cota
de aceitos. Depois, `merge-cache` reúne as pastas `data/cache` (escolhe a
melhor cópia de cada repositório).

## Saídas

| Arquivo | Conteúdo |
|---|---|
| `data/candidates.json` | candidatos da busca (compartilhado pelo grupo) |
| `data/funil.md/.json`, `data/funil_tabela.tex` | funil de seleção (vai para a Metodologia) |
| `data/selecao_repositorios.csv` | decisão por repositório (aceito/descartado + motivo) |
| `data/dataset/dataset_repos.csv` | **dataset final** (1 linha por repositório) |
| `data/dataset/dicionario_dados.csv`, `docs/DICIONARIO_DADOS.md` | dicionário de dados |
| `data/validacao/` | amostra-ouro, rótulos de cada avaliador, consenso, kappa, F1 |

## Definições operacionais adotadas

Seguem a seção 3 do enunciado. Decisões do grupo onde o enunciado deixa margem:

- **Deploy** = release com `draft=false` e `prerelease=false`, `published_at` na janela. Pré-releases são coletadas (campo `prerelease`) para a RQ 07.
- **Commits de uma release** vêm de `compare/{release anterior}...{R}` — **não** de um filtro por data. Assim, um commit escrito antes da release anterior mas só incluído agora continua contando (é o que faz o lead time (a) "explodir"). Os commits **não** são filtrados pela janela; só as releases são. A release anterior à primeira da janela pode estar fora dela.
- **Runs válidos** (critério ≥ 50): `push` no default branch, criados na janela, com `conclusion` em `success` ou `failure/timed_out/startup_failure`. `cancelled`, `skipped` etc. são ignorados em tudo.
- **Recuperação**: por workflow; episódio = 1ª falha após sucesso → próximo sucesso (`updated_at − run_started_at`); sem sucesso depois = **censurado** (reportado, não descartado).
- **CFR (b)**: R falha se houver release corretiva em (R, R+7 d]; releases dos últimos 7 dias da janela são censuradas. A heurística tem versões (`src/metricas/heuristica.py`) avaliadas contra o consenso humano.
- **Compare 404/422** (tag apagada): release ignorada no lead time e contada em `lt_n_releases_compare_404`.
- Lista de contribuidores via `?per_page=1&anon=true` (nº da última página do cabeçalho `Link`).

## Testes e CI

```bash
pytest -q
pytest --cov=src.metricas --cov-report=term-missing   # exigência: >= 80% (hoje ~95%)
```

O workflow está em `.github/workflows/lab3-tests.yml` (**na raiz do repositório**).
Os testes usam um GitHub falso em memória (`tests/fake_github.py`); os
exemplos numéricos do enunciado (lead time de 13 dias, CFR de `v2.3.0`,
recuperação de 1h20, precisão 75%/recall 60%) são casos de teste.

## Estrutura

```
src/collectors/   repositories.py (cliente, busca, cache, runs, releases) · commits_compare.py
src/metricas/     ci.py (CFR a, recuperação) · lead_time.py · heuristica.py · cfr_release.py
src/pipeline/     __main__.py (CLI) · selecao.py · funil.py · dataset.py · dicionario.py · merge.py · config.py
src/validacao/    amostra_ouro.py · concordancia.py · avaliar_heuristica.py
tools/            rotulador.html (rotulagem manual, funciona offline no navegador)
docs/             plano da sprint, protocolo de validação, heurística, artigo (metodologia)
tests/
```

## Regras do processo

- Todo commit referencia a Issue (`#N`) — commits sem número não são considerados na correção.
- Cada integrante é *Assignee* de ao menos uma Issue com código commitado na sprint.
- Respeitar o WIP no GitHub Projects e manter os cartões atualizados.
- O token fica só no `.env`/variável de ambiente.
