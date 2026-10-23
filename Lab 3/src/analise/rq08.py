"""RQ 08 (bônus, opção "rework rate"): releases corretivas ÷ releases.

Compara com o CFR (b): o CFR (b) olha a release que **precisou** de
correção (a anterior à corretiva, até 7 dias), o rework rate conta as
**próprias** releases corretivas, sem janela de 7 dias e sem censura.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from scipy.stats import spearmanr, wilcoxon

from src.analise.comum import descrever, fmt, fmt_p, salvar_tabela


def executar(df: pd.DataFrame, destino: Path) -> dict[str, Any]:
    rework, cfr_b = df["rework_rate"] * 100, df["cfr_entrega"] * 100
    linhas = []
    for rotulo, serie in (("Rework rate", rework), ("CFR (b)", cfr_b)):
        d = descrever(serie)
        linhas.append({"Métrica": rotulo, "Unidade": "%", "n": fmt(d["n"]),
                       "Q1": fmt(d["q1"], 1), "Mediana": fmt(d["mediana"], 1), "Q3": fmt(d["q3"], 1)})

    par = pd.DataFrame({"r": rework, "c": cfr_b}).dropna()
    resultado: dict[str, Any] = {"n": len(par)}
    if len(par) >= 3 and par["r"].nunique() > 1 and par["c"].nunique() > 1:
        rho, p = spearmanr(par["r"], par["c"])
        resultado.update(rho=float(rho), p_rho=float(p))
    diferencas = par["r"] - par["c"]
    if (diferencas != 0).sum() >= 1:
        _, p_w = wilcoxon(par["r"], par["c"])
        resultado["p_wilcoxon"] = float(p_w)
    resultado["prop_rework_maior"] = float((diferencas > 0).mean()) if len(par) else None

    linhas.append({"Métrica": "Spearman rework × CFR (b)", "Unidade": "ρ",
                   "n": fmt(len(par)), "Q1": "", "Mediana": fmt(resultado.get("rho"), 3),
                   "Q3": f"p = {fmt_p(resultado.get('p_rho'))}"})
    salvar_tabela(linhas, destino, "tab_rq08",
                  "RQ 08 (bônus): rework rate comparado ao CFR (b).")
    return resultado
