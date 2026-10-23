"""RQ 05: correlação de Spearman entre deployment frequency e CFR (a) e (b).

Saídas: ``tab_rq05`` (ρ, p-valor, n) e ``figuras/rq05_dispersao.png``
(eixo x em escala logarítmica).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd
from scipy.stats import spearmanr

from src.analise.comum import (
    AZUL, GRADE, TINTA, eixo_log, fmt, fmt_p, salvar_figura, salvar_tabela,
)

VARIANTES = [("CFR (a) proxy de CI", "cfr_ci"), ("CFR (b) proxy de entrega", "cfr_entrega")]


def interpretar_rho(rho: float) -> str:
    """Força da correlação (faixas usuais: < 0,1 desprezível; < 0,3 fraca;
    < 0,5 moderada; >= 0,5 forte)."""

    a = abs(rho)
    forca = ("desprezível" if a < 0.1 else "fraca" if a < 0.3
             else "moderada" if a < 0.5 else "forte")
    sentido = "positiva" if rho > 0 else "negativa" if rho < 0 else ""
    return f"{forca} {sentido}".strip()


def correlacoes(df: pd.DataFrame) -> list[dict[str, Any]]:
    resultados = []
    for rotulo, coluna in VARIANTES:
        par = df[["deploy_freq_semana", coluna]].dropna()
        if len(par) < 3 or par[coluna].nunique() < 2:
            resultados.append({"variante": rotulo, "rho": None, "p": None, "n": len(par)})
            continue
        rho, p = spearmanr(par["deploy_freq_semana"], par[coluna])
        resultados.append({"variante": rotulo, "rho": float(rho), "p": float(p), "n": len(par)})
    return resultados


def figura(df: pd.DataFrame, resultados: list[dict[str, Any]], destino: Path) -> None:
    """Dispersão (exigida pelo enunciado), eixo x em log, ρ escrito no painel."""

    fig, eixos = plt.subplots(1, 2, figsize=(10, 3.8), sharex=True)
    for eixo, (rotulo, coluna), r in zip(eixos, VARIANTES, resultados):
        par = df[["deploy_freq_semana", coluna]].dropna()
        par = par[par["deploy_freq_semana"] > 0]
        eixo.scatter(par["deploy_freq_semana"], par[coluna] * 100, s=16, alpha=0.55,
                     color=AZUL, edgecolor="white", linewidth=0.4)
        eixo_log(eixo, "x")
        eixo.set_xlabel("Deployment frequency (releases/semana, escala log)")
        eixo.set_ylabel(f"{rotulo} (%)")
        eixo.set_title(rotulo, loc="left")
        eixo.grid(True)
        eixo.set_axisbelow(True)
        if r["rho"] is not None:
            texto = (f"ρ de Spearman = {fmt(r['rho'], 2)}\np = {fmt_p(r['p'])} · n = {r['n']}\n"
                     f"({interpretar_rho(r['rho'])})")
            eixo.text(0.98, 0.97, texto, transform=eixo.transAxes, ha="right", va="top",
                      fontsize=8, color=TINTA,
                      bbox={"boxstyle": "round,pad=0.4", "facecolor": "white", "edgecolor": GRADE})
    salvar_figura(fig, destino, "rq05_dispersao")


def executar(df: pd.DataFrame, destino: Path) -> list[dict[str, Any]]:
    resultados = correlacoes(df)
    salvar_tabela(
        [{"Variante": r["variante"], "ρ de Spearman": fmt(r["rho"], 3),
          "p-valor": fmt_p(r["p"]), "n": fmt(r["n"]),
          "Interpretação": interpretar_rho(r["rho"]) if r["rho"] is not None else "--"}
         for r in resultados],
        destino, "tab_rq05",
        "Correlação de Spearman entre deployment frequency e change failure rate.",
    )
    figura(df, resultados, destino)
    return resultados
