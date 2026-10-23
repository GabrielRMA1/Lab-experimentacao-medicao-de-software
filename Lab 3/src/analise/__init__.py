"""Análises da Sprint 03 (RQ 01–08), reexecutáveis a partir do CSV.

Uso: ``python -m src.pipeline analise`` (lê ``data/dataset/dataset_repos.csv``
e grava tabelas .tex/.csv, figuras e ``resumo.md`` em ``data/resultados``).

Cada RQ é um módulo próprio: ``rq01_04``, ``rq05``, ``rq06``, ``rq07``, ``rq08``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.analise.comum import (
    DATASET_PADRAO, SAIDA_PADRAO, VALIDACAO_PADRAO, carregar_dataset, fmt, fmt_p,
)


def _linha_descr(nome: str, d: dict[str, Any], casas: int = 1) -> str:
    return (f"- {nome}: mediana {fmt(d['mediana'], casas)} "
            f"(IQR {fmt(d['q1'], casas)}–{fmt(d['q3'], casas)}), n = {d['n']}")


def executar_tudo(
    dataset: Path = DATASET_PADRAO,
    destino: Path = SAIDA_PADRAO,
    validacao_dir: Path | None = VALIDACAO_PADRAO,
) -> Path:
    from src.analise import rq01_04, rq05, rq06, rq07, rq08

    df = carregar_dataset(dataset)
    destino.mkdir(parents=True, exist_ok=True)

    r14 = rq01_04.executar(df, destino)
    r5 = rq05.executar(df, destino)
    r6 = rq06.executar(df, destino, validacao_dir)
    r7 = rq07.executar(df, destino)
    r8 = rq08.executar(df, destino)

    texto = [f"# Resumo dos resultados ({len(df)} repositórios)", "",
             "Gerado por `python -m src.pipeline analise`. Use estes números no artigo.", "",
             "## RQ 01–04 (mediana e IQR entre repositórios)"]
    for nome, d in r14.items():
        if isinstance(d, dict) and "mediana" in d:
            texto.append(_linha_descr(nome, d))
    texto += ["", f"Categorias DORA (C1): {r14['categorias_c1']}; "
              f"não classificáveis: {r14['nao_classificaveis_c1']}", "",
              "## RQ 05 (Spearman, deploy freq × CFR)"]
    for r in r5:
        texto.append(f"- {r['variante']}: ρ = {fmt(r['rho'], 3)}, p = {fmt_p(r['p'])}, n = {r['n']}")
    texto += ["", f"## RQ 06 ({len(r6)} testes, Holm)"]
    for t in sorted(r6, key=lambda t: t["p_holm"]):
        marca = "**significativo**" if t["significativo"] else "n.s."
        texto.append(f"- {t['fator']} × {t['metrica']}: {t['teste']}, p_holm = "
                     f"{fmt_p(t['p_holm'])} ({marca}), {t['efeito']} ({t['magnitude']})")
    texto += ["", "## RQ 07 (sensibilidade)"]
    for p in r7["pares"]:
        mud = "--" if p["mudaram"] is None else f"{fmt(100 * p['mudaram'], 1)}%"
        texto.append(f"- {p['par']}: {mud} mudaram de categoria; kappa ponderado = "
                     f"{fmt(p['kappa'], 3)} (n = {p['n']})")
    texto += ["", "## RQ 08 (bônus: rework rate)",
              f"- Spearman rework × CFR (b): ρ = {fmt(r8.get('rho'), 3)}, "
              f"p = {fmt_p(r8.get('p_rho'))}, n = {r8['n']}",
              f"- Wilcoxon pareado: p = {fmt_p(r8.get('p_wilcoxon'))}; repositórios com rework > CFR (b): "
              f"{fmt(100 * r8['prop_rework_maior'], 1) if r8.get('prop_rework_maior') is not None else '--'}%",
              ""]
    caminho = destino / "resumo.md"
    caminho.write_text("\n".join(texto), encoding="utf-8")
    brutos = {"n_repositorios": len(df), "rq01_04": r14, "rq05": r5, "rq06": r6,
              "rq07": {"pares": r7["pares"]}, "rq08": r8}
    (destino / "resultados.json").write_text(
        json.dumps(brutos, ensure_ascii=False, indent=2, default=_json_padrao), encoding="utf-8")
    return caminho


def _json_padrao(valor: Any) -> Any:
    """Converte tipos do numpy/pandas para JSON (NaN vira null)."""

    import math

    if hasattr(valor, "item"):
        valor = valor.item()
    if isinstance(valor, float) and math.isnan(valor):
        return None
    if isinstance(valor, (bool, int, float, str)) or valor is None:
        return valor
    return str(valor)
