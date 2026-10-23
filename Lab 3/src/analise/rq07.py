"""RQ 07: análise de sensibilidade da classificação DORA.

Combinações de definições operacionais (todas calculadas a partir do CSV):

| Combinação | Unidade de deploy        | Lead time | CFR |
|------------|--------------------------|-----------|-----|
| C1 (ref.)  | release                  | (a)       | (a) |
| C2         | release + pré-release    | (b)       | (b) |
| C3         | release                  | (b)       | (a) |
| C4         | release                  | (a)       | (b) |

C3 e C4 mudam **uma** definição por vez em relação a C1, o que permite
atribuir a mudança de categoria ao lead time ou ao CFR. Em C2, a
pré-release entra na frequência de deploy; o lead time continua medido
pelas releases estáveis (o ``compare`` das pré-releases não foi coletado —
limitação registrada nas ameaças à validade). A variante "tag" do
enunciado não foi coletada.

Para cada par: % de repositórios que mudaram de categoria e kappa de Cohen
ponderado (linear), só com repositórios classificáveis nas duas.
"""

from __future__ import annotations

from itertools import combinations
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import cohen_kappa_score

from src.analise.comum import fmt, salvar_figura, salvar_tabela, semanas_da_janela
from src.metricas.dora import NOMES, ORDEM, classificar

COMBINACOES = {
    "C1": {"deploy": "release", "lt": "lt_release_mediana_h", "cfr": "cfr_ci",
           "descricao": "release, lead time (a), CFR (a)"},
    "C2": {"deploy": "release+pre", "lt": "lt_commit_mediana_h", "cfr": "cfr_entrega",
           "descricao": "release + pré-release, lead time (b), CFR (b)"},
    "C3": {"deploy": "release", "lt": "lt_commit_mediana_h", "cfr": "cfr_ci",
           "descricao": "release, lead time (b), CFR (a)"},
    "C4": {"deploy": "release", "lt": "lt_release_mediana_h", "cfr": "cfr_entrega",
           "descricao": "release, lead time (a), CFR (b)"},
}


def interpretar_kappa(k: float | None) -> str:
    if k is None or np.isnan(k):
        return "--"
    return ("pobre" if k < 0 else "leve" if k <= 0.20 else "razoável" if k <= 0.40
            else "moderada" if k <= 0.60 else "substancial" if k <= 0.80 else "quase perfeita")


def frequencia(df: pd.DataFrame, unidade: str) -> pd.Series:
    if unidade == "release":
        return df["deploy_freq_semana"]
    semanas = semanas_da_janela(df)
    return (df["n_releases"] + df["n_prereleases_janela"].fillna(0)) / semanas


def classificar_combinacoes(df: pd.DataFrame) -> pd.DataFrame:
    saida = df[["full_name"]].copy()
    for nome, c in COMBINACOES.items():
        freq = frequencia(df, c["deploy"])
        resultado = [
            classificar(f, lt, cfr, rec)
            for f, lt, cfr, rec in zip(freq, df[c["lt"]], df[c["cfr"]], df["rec_mediana_h"])
        ]
        saida[nome] = [r["geral"] for r in resultado]
        saida[f"{nome}_categoria"] = [r["categoria"] for r in resultado]
    return saida


def comparar_pares(classes: pd.DataFrame) -> list[dict[str, Any]]:
    linhas = []
    for a, b in combinations(COMBINACOES, 2):
        par = classes[[a, b]].dropna()
        n = len(par)
        if n == 0:
            linhas.append({"par": f"{a} × {b}", "n": 0, "mudaram": None, "kappa": None})
            continue
        mudaram = float((par[a] != par[b]).mean())
        if par[a].nunique() + par[b].nunique() > 2:
            kappa = float(cohen_kappa_score(par[a].astype(int), par[b].astype(int),
                                            weights="linear", labels=[1, 2, 3, 4]))
        else:
            kappa = float("nan")
        linhas.append({"par": f"{a} × {b}", "n": n, "mudaram": mudaram, "kappa": kappa})
    return linhas


EIXOS_RADAR = [("Deploy freq.", "nivel_df"), ("Lead time", "nivel_lt"), ("CFR", "nivel_cfr"),
               ("Recuperação", "nivel_rec"), ("Geral", "geral")]


def perfil_elite_high(df: pd.DataFrame, nome: str) -> list[float]:
    """% de repositórios Elite ou High em cada métrica e na categoria geral."""

    c = COMBINACOES[nome]
    freq = frequencia(df, c["deploy"])
    res = pd.DataFrame([classificar(f, lt, cfr, rec) for f, lt, cfr, rec in
                        zip(freq, df[c["lt"]], df[c["cfr"]], df["rec_mediana_h"])])
    perfil = []
    for _, col in EIXOS_RADAR:
        validos = res[col].dropna()
        perfil.append(100 * float((validos >= 3).mean()) if len(validos) else 0.0)
    return perfil


def figura(df: pd.DataFrame, pares: list[dict[str, Any]], destino: Path) -> None:
    """Radar em painéis: cada combinação (azul) sobre a referência C1 (cinza)."""

    from src.analise.comum import AZUL, CINZA_REF, TINTA_2

    angulos = np.linspace(0, 2 * np.pi, len(EIXOS_RADAR), endpoint=False).tolist()
    fechar = angulos + angulos[:1]
    referencia = perfil_elite_high(df, "C1")
    outras = [n for n in COMBINACOES if n != "C1"]
    por_par = {p["par"]: p for p in pares}
    fig, eixos = plt.subplots(1, len(outras), figsize=(4 * len(outras), 4),
                              subplot_kw={"polar": True})
    for eixo, nome in zip(np.atleast_1d(eixos), outras):
        perfil = perfil_elite_high(df, nome)
        eixo.plot(fechar, referencia + referencia[:1], color=CINZA_REF, linewidth=1.5,
                  linestyle="--", label="C1 (referência)")
        eixo.plot(fechar, perfil + perfil[:1], color=AZUL, linewidth=2, label=nome)
        eixo.fill(fechar, perfil + perfil[:1], color=AZUL, alpha=0.15)
        eixo.set_xticks(angulos, [r for r, _ in EIXOS_RADAR], fontsize=10)
        eixo.set_ylim(0, 100)
        eixo.set_yticks([25, 50, 75, 100], ["25%", "50%", "75%", "100%"], fontsize=7, color=TINTA_2)
        eixo.set_rlabel_position(36)  # rótulos de % entre dois eixos, sem colidir
        eixo.spines["polar"].set_visible(False)
        eixo.grid(color="#e4e3df")
        p = por_par.get(f"C1 × {nome}")
        sub = "" if p is None or p["mudaram"] is None else (
            f"\n{fmt(100 * p['mudaram'], 0)}% mudam de categoria · κ = {fmt(p['kappa'], 2)}")
        eixo.set_title(f"{nome}: {COMBINACOES[nome]['descricao']}{sub}", fontsize=10, pad=20)
        eixo.legend(loc="lower center", bbox_to_anchor=(0.5, -0.3), ncol=2, fontsize=9.5, frameon=False)
    fig.suptitle("RQ 07 · % de repositórios Elite ou High em cada definição", x=0.01,
                 ha="left", fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    salvar_figura(fig, destino, "rq07_radar", ajustar=False)


def executar(df: pd.DataFrame, destino: Path) -> dict[str, Any]:
    classes = classificar_combinacoes(df)
    classes.to_csv(destino / "classificacao_combinacoes.csv", index=False)
    pares = comparar_pares(classes)

    distribuicao = []
    for nome, c in COMBINACOES.items():
        cats = classes[f"{nome}_categoria"]
        linha: dict[str, Any] = {"Combinação": nome, "Definições": c["descricao"]}
        for cat in ORDEM:
            linha[cat] = fmt(int((cats == cat).sum()))
        linha["Não classif."] = fmt(int(cats.isna().sum()))
        distribuicao.append(linha)
    salvar_tabela(distribuicao, destino, "tab_rq07_distribuicao",
                  "Distribuição das categorias DORA em cada combinação de definições.",
                  alinhamento="llrrrrr")
    salvar_tabela(
        [{"Par": p["par"], "n": fmt(p["n"]),
          "Mudaram de categoria": f"{fmt(100 * p['mudaram'], 1)}%" if p["mudaram"] is not None else "--",
          "Kappa ponderado": fmt(p["kappa"], 3), "Concordância": interpretar_kappa(p["kappa"])}
         for p in pares],
        destino, "tab_rq07_pares",
        "Sensibilidade: repositórios que mudam de categoria e kappa de Cohen ponderado (linear).",
    )
    figura(df, pares, destino)
    return {"pares": pares, "nomes": NOMES}
