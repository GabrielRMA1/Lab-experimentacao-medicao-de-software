# Heurística de release corretiva (RQ 03 b)

Uma release é **corretiva** quando seu objetivo principal é corrigir um defeito
recente. O CFR (b) marca a release R como **falha** se uma release corretiva
for publicada em até 7 dias depois dela (`src/metricas/cfr_release.py`).

## Sinais usados (`src/metricas/heuristica.py`)
| Sinal | Definição |
|---|---|
| `patch_bump` | só o *patch* subiu em relação à release imediatamente anterior (`2.3.0 → 2.3.1`). Versões de calendário (`2024.05.10`) não contam. |
| `kw_ratio` | fração dos commits da release cuja 1ª linha casa com `revert`, `hotfix`, `bugfix` ou `fix(es/ed/ing)` (palavra inteira; `prefix`/`fixture` não casam). |
| `kw_any` | existe ao menos um commit assim. |
| `notes_kw` | título ou primeiros 300 caracteres das notas citam hotfix, regression, revert, emergency, patch release, bugfix release. |

## Versões
| Versão | Regra |
|---|---|
| `v1_patch` | `patch_bump` |
| `v2_palavras` | `kw_ratio ≥ 0,5` |
| `v3_patch_ou_palavras` *(padrão até a validação)* | `patch_bump` **ou** `kw_ratio ≥ 0,5` |
| `v4_patch_e_palavras` | `patch_bump` **e** `kw_any` |
| `v5_refinada` | (`patch_bump` e (`kw_ratio ≥ 0,25` ou `notes_kw`)) ou (`kw_ratio ≥ 0,5` e ≤ 30 commits) ou `notes_kw` |

Os limiares (0,5; 0,25; 30; 300 caracteres) são **pontos de partida**, não
resultados de ajuste. As versões v2–v5 só combinam as pistas sugeridas no enunciado.

## Registro de avaliação (preencher com `python -m src.pipeline heuristica`)
Cada tentativa — inclusive as ruins — entra aqui e no artigo.

| # | Versão | n | Precisão | Recall | F1 | Mudança feita / motivo |
|---|---|---|---|---|---|---|
| 1 | v1_patch | | | | | |
| 2 | v2_palavras | | | | | |
| 3 | v3_patch_ou_palavras | | | | | |
| 4 | v4_patch_e_palavras | | | | | |
| 5 | v5_refinada | | | | | |
| 6 | *(v6, se F1 < 0,70)* | | | | | |

**Meta:** F1 ≥ 0,70 na melhor versão (enunciado). Se não for atingida, refinar e reavaliar.

## Como refinar (sem "colar" no gabarito)
1. Veja os **falsos positivos e falsos negativos** (releases onde a versão discorda do consenso) e agrupe os motivos (ex.: "patch de dependência", "revert sem palavra-chave na 1ª linha").
2. Acrescente uma versão nova (`v6_...`) em `VERSIONS` — **não edite as antigas** — para o histórico continuar reproduzível.
3. Reavalie e registre. Parar quando o ganho de F1 virar ruído.

## Ameaças que este documento alimenta
- **Construto:** "corretiva" é um conceito humano; releases de patch podem ser rotineiras e releases minor podem ser hotfix.
- **Conclusão:** a versão vencedora foi escolhida no mesmo conjunto em que foi avaliada (otimismo); amostra de ~300 releases (menos, se a rotulagem for parcial) gera IC largo para o F1.
- **Interna:** a 1ª linha do commit não reflete squash/merge commits ("Merge pull request…") — pode subestimar `kw_ratio`.
