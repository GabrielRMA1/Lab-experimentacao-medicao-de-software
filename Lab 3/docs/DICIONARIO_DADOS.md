# Dicionário de dados — `data/dataset/dataset_repos.csv`

Uma linha por repositório da amostra final. Gerado por `python -m src.pipeline consolidate` (não edite à mão: edite `src/pipeline/dicionario.py`).

Valores vazios significam *não calculável* (ex.: nenhum episódio de falha ⇒ `rec_mediana_h` vazio). Janela de observação: ver `data/funil.json`.

| Coluna | Tipo | Unidade | Origem / fórmula | RQ |
|---|---|---|---|---|
| `full_name` | texto | — | `full_name` da Search API (dono/repositório) | — |
| `html_url` | texto | — | `html_url` da API | — |
| `language` | texto | — | Linguagem principal (`language`); vazio se a API não informa | RQ 06 |
| `stars` | inteiro | estrelas | `stargazers_count` na data da busca | RQ 06 |
| `forks` | inteiro | forks | `forks_count` na data da busca | — |
| `contributors` | inteiro | pessoas | Nº da última página de `GET /contributors?per_page=1&anon=true` | RQ 06 |
| `created_at` | data ISO 8601 (UTC) | — | `created_at` do repositório | RQ 06 |
| `idade_dias_fim_janela` | inteiro | dias | `OBSERVATION_END` − `created_at` | RQ 06 |
| `default_branch` | texto | — | `default_branch` da API (única branch considerada) | — |
| `n_releases` | inteiro | releases | Releases com `draft=false` e `prerelease=false` e `published_at` na janela | RQ 01 |
| `n_prereleases_janela` | inteiro | releases | Pré-releases (`prerelease=true`) publicadas na janela (variante da RQ 07) | RQ 07 |
| `deploy_freq_semana` | decimal | releases/semana | `n_releases` ÷ (dias da janela ÷ 7) | RQ 01 |
| `lt_release_mediana_h` | decimal | horas | Mediana, entre as releases da janela, de (`published_at` de R − commit mais antigo de R); commits via `compare` | RQ 02a |
| `lt_release_q1_h` | decimal | horas | 1º quartil (método inclusivo) do lead time por release | RQ 02a |
| `lt_release_q3_h` | decimal | horas | 3º quartil do lead time por release | RQ 02a |
| `lt_commit_mediana_h` | decimal | horas | Mediana de (`published_at` de R − `commit.author.date`) sobre todos os commits de todas as releases | RQ 02b |
| `lt_commit_q1_h` | decimal | horas | 1º quartil do lead time por commit | RQ 02b |
| `lt_commit_q3_h` | decimal | horas | 3º quartil do lead time por commit | RQ 02b |
| `lt_n_releases_avaliadas` | inteiro | releases | Releases com ≥ 1 commit válido (entram na mediana (a)) | RQ 02 |
| `lt_n_commits` | inteiro | commits | Commits usados na mediana (b) | RQ 02 |
| `lt_n_releases_compare_404` | inteiro | releases | Releases ignoradas porque `compare` retornou 404/422 (tag apagada/reescrita) | RQ 02 |
| `ci_n_sucessos` | inteiro | runs | Runs `push` na default branch, na janela, com `conclusion = success` | RQ 03a |
| `ci_n_falhas` | inteiro | runs | Idem com `conclusion` ∈ {failure, timed_out, startup_failure} | RQ 03a |
| `cfr_ci` | decimal 0–1 | proporção | `ci_n_falhas` ÷ (`ci_n_falhas` + `ci_n_sucessos`) | RQ 03a |
| `heuristica_versao` | texto | — | Versão da heurística de release corretiva usada (ver `docs/HEURISTICA_CORRETIVA.md`) | RQ 03b |
| `cfr_n_avaliadas` | inteiro | releases | Releases da janela publicadas ≥ 7 dias antes do fim da janela | RQ 03b |
| `cfr_n_falhas` | inteiro | releases | Releases avaliadas seguidas, em até 7 dias, por uma release corretiva | RQ 03b |
| `cfr_n_censuradas` | inteiro | releases | Releases publicadas nos últimos 7 dias da janela (fora do denominador) | RQ 03b |
| `cfr_entrega` | decimal 0–1 | proporção | `cfr_n_falhas` ÷ `cfr_n_avaliadas` | RQ 03b |
| `n_releases_corretivas` | inteiro | releases | Releases da janela marcadas como corretivas pela heurística | RQ 08 |
| `rework_rate` | decimal 0–1 | proporção | `n_releases_corretivas` ÷ `n_releases` | RQ 08 |
| `rec_n_episodios` | inteiro | episódios | Episódios de falha (1ª falha após sucesso, por workflow), incluindo censurados | RQ 04 |
| `rec_n_censurados` | inteiro | episódios | Episódios sem sucesso posterior dentro da janela | RQ 04 |
| `rec_prop_censurados` | decimal 0–1 | proporção | `rec_n_censurados` ÷ `rec_n_episodios` | RQ 04 |
| `rec_mediana_h` | decimal | horas | Mediana de (`updated_at` do sucesso − `run_started_at` da 1ª falha) nos episódios recuperados, de todos os workflows | RQ 04 |
| `rec_q1_h` | decimal | horas | 1º quartil do tempo de recuperação | RQ 04 |
| `rec_q3_h` | decimal | horas | 3º quartil do tempo de recuperação | RQ 04 |
| `coleta_incompleta` | booleano | — | `True` se algum intervalo de `compare` do cache não terminou de ser coletado | — |
