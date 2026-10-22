"""RQ 01–04: estatística descritiva (mediana e IQR) e classificação DORA C1.

Saídas (em ``data/resultados``):
* ``tab_rq01_04`` (.csv/.tex) — mediana e IQR de cada métrica e variante;
* ``tab_censura`` — casos censurados e releases ignoradas (vai para o texto);
* ``tab_dora_c1`` — distribuição Elite/High/Medium/Low por métrica e geral;
* ``classificacao_c1.csv`` — classificação de cada repositório;
* ``figuras/rq01_04_distribuicoes.png`` (violinos das quatro métricas).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.analise.comum import (
    AZUL, HORAS_POR_DIA, LARANJA, TINTA, TINTA_2, descrever, fmt, salvar_figura,
    salvar_tabela,
)
from src.metricas.dora import NOMES, ORDEM, classificar

# (rótulo, coluna, unidade de exibição, fator de conversão, casas, RQ)
METRICAS = [
    ("Deployment frequency", "deploy_freq_semana", "releases/semana", 1.0, 2, "RQ 01"),
    ("Lead time (a) por release", "lt_release_mediana_h", "dias", 1 / HORAS_POR_DIA, 1, "RQ 02a"),
    ("Lead time (b) por commit", "lt_commit_mediana_h", "dias", 1 / HORAS_POR_DIA, 1, "RQ 02b"),
    ("CFR (a) proxy de CI", "cfr_ci", "%", 100.0, 1, "RQ 03a"),
    ("CFR (b) proxy de entrega", "cfr_entrega", "%", 100.0, 1, "RQ 03b"),
    ("Tempo de recuperação", "rec_mediana_h", "horas", 1.0, 1, "RQ 04"),
    ("Episódios censurados", "rec_prop_censurados", "% por repo", 100.0, 1, "RQ 04"),
]


def classificar_c1(df: pd.DataFrame) -> pd.DataFrame:
    """C1 (referência): release, lead time (a), CFR (a), recuperação."""

    linhas = [
        classificar(r.deploy_freq_semana, r.lt_release_mediana_h, r.cfr_ci, r.rec_mediana_h)
        for r in df.itertuples()
    ]
    return pd.concat([df[["full_name"]].reset_index(drop=True), pd.DataFrame(linhas)], axis=1)


def tabela_descritiva(df: pd.DataFrame) -> list[dict[str, Any]]:
    linhas = []
    for rotulo, coluna, unidade, fator, casas, rq in METRICAS:
        d = descrever(df[coluna] * fator)
        linhas.append({
            "RQ": rq, "Métrica": rotulo, "Unidade": unidade, "n": fmt(d["n"]),
            "Q1": fmt(d["q1"], casas), "Mediana": fmt(d["mediana"], casas),
            "Q3": fmt(d["q3"], casas),
        })
    return linhas


def tabela_censura(df: pd.DataFrame) -> list[dict[str, Any]]:
    ep, cens = int(df["rec_n_episodios"].sum()), int(df["rec_n_censurados"].sum())
    aval, rcens = int(df["cfr_n_avaliadas"].sum()), int(df["cfr_n_censuradas"].sum())
    linhas = [
        {"Item": "Episódios de falha (RQ 04)", "Total": fmt(ep),
         "Censurados ou ignorados": fmt(cens), "%": fmt(100 * cens / ep if ep else None, 1)},
        {"Item": "Releases para o CFR (b) (RQ 03b)", "Total": fmt(aval + rcens),
         "Censurados ou ignorados": fmt(rcens), "%": fmt(100 * rcens / (aval + rcens) if aval + rcens else None, 1)},
        {"Item": "Releases com compare 404/422 (RQ 02)", "Total": fmt(int(df["n_releases"].sum())),
         "Censurados ou ignorados": fmt(int(df["lt_n_releases_compare_404"].sum())), "%": "--"},
    ]
    if "runs_intervalos_truncados" in df:
        linhas.append({"Item": "Repositórios com runs truncados (teto 1.000)",
                       "Total": fmt(len(df)),
                       "Censurados ou ignorados": fmt(int((df["runs_intervalos_truncados"] > 0).sum())),
                       "%": "--"})
    return linhas


def tabela_dora(classes: pd.DataFrame) -> list[dict[str, Any]]:
    colunas = [("Deployment frequency", "nivel_df"), ("Lead time (a)", "nivel_lt"),
               ("CFR (a)", "nivel_cfr"), ("Recuperação", "nivel_rec"), ("Geral", "geral")]
    linhas = []
    for rotulo, col in colunas:
        nomes = classes[col].map(NOMES)
        total = int(nomes.notna().sum())
        linha: dict[str, Any] = {"Métrica": rotulo}
        for cat in ORDEM:
            k = int((nomes == cat).sum())
            linha[cat] = f"{k} ({fmt(100 * k / total if total else None, 0)}%)"
        linha["Sem nível"] = fmt(int(nomes.isna().sum()))
        linhas.append(linha)
    return linhas


def _violino(eixo, series: list[pd.Series], rotulos: list[str], log: bool,
             unidade: str, casas: int) -> None:
    """Violino por série, com caixa do IQR, ponto na mediana e o valor escrito.

    Em escala log, a densidade é estimada sobre log10 dos valores (a forma
    fica correta) e os rótulos do eixo voltam para a unidade original.
    """

    cores = [AZUL, LARANJA]
    for i, (serie, rotulo) in enumerate(zip(series, rotulos)):
        dados = serie.dropna().to_numpy(dtype=float)
        if log:
            dados = dados[dados > 0]
        if dados.size < 2:
            continue
        valores = np.log10(dados) if log else dados
        partes = eixo.violinplot([valores], positions=[i], widths=0.8,
                                 showextrema=False, showmedians=False)
        for corpo in partes["bodies"]:
            corpo.set_facecolor(cores[i % 2])
            corpo.set_edgecolor(cores[i % 2])
            corpo.set_alpha(0.35)
        q1, med, q3 = np.percentile(valores, [25, 50, 75])
        eixo.vlines(i, q1, q3, color=cores[i % 2], linewidth=5, zorder=3)
        eixo.scatter([i], [med], s=28, color="white", edgecolor=TINTA, linewidth=1.2, zorder=4)
        mediana_real = 10 ** med if log else med
        eixo.annotate(f"{fmt(mediana_real, casas)} {unidade}", (i, med), xytext=(14, 0),
                      textcoords="offset points", va="center", fontsize=8, color=TINTA)
    eixo.set_xticks(range(len(rotulos)), rotulos)
    eixo.set_xlim(-0.75, 0.95) if len(rotulos) == 1 else eixo.set_xlim(-0.6, len(rotulos) - 0.1)
    eixo.grid(axis="y")
    eixo.set_axisbelow(True)
    if log:
        from matplotlib.ticker import FixedLocator, FuncFormatter

        baixo, alto = eixo.get_ylim()
        marcas = [np.log10(m * 10 ** k) for k in range(int(np.floor(baixo)) - 1, int(np.ceil(alto)) + 1)
                  for m in (1, 2, 5) if baixo <= np.log10(m * 10 ** k) <= alto]
        eixo.yaxis.set_major_locator(FixedLocator(marcas))
        eixo.yaxis.set_major_formatter(
            FuncFormatter(lambda v, _: f"{10 ** v:g}".replace(".", ",")))


def figura_distribuicoes(df: pd.DataFrame, destino: Path) -> None:
    """Uma figura para as RQ 01–04: distribuição entre repositórios."""

    fig, eixos = plt.subplots(2, 2, figsize=(9, 7))
    eixos = eixos.ravel()
    paineis = [
        ("RQ 01 · Deployment frequency\n(releases/semana, log)",
         [df["deploy_freq_semana"]], ["release"], True, "/sem", 2),
        ("RQ 02 · Lead time\n(dias, log)",
         [df["lt_release_mediana_h"] / 24, df["lt_commit_mediana_h"] / 24],
         ["(a) release", "(b) commit"], True, "d", 1),
        ("RQ 03 · Change failure rate\n(%)",
         [df["cfr_ci"] * 100, df["cfr_entrega"] * 100], ["(a) CI", "(b) entrega"], False, "%", 1),
        ("RQ 04 · Tempo de recuperação\n(horas, log)",
         [df["rec_mediana_h"]], ["mediana/repo"], True, "h", 1),
    ]
    for eixo, (titulo, series, rotulos, log, unidade, casas) in zip(eixos, paineis):
        _violino(eixo, series, rotulos, log, unidade, casas)
        eixo.set_title(titulo, loc="left")
    fig.text(0.01, 0.01, "Ponto branco = mediana; barra = IQR (Q1–Q3); "
             "área = distribuição dos repositórios.", fontsize=8, color=TINTA_2)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    salvar_figura(fig, destino, "rq01_04_distribuicoes", ajustar=False)


def executar(df: pd.DataFrame, destino: Path) -> dict[str, Any]:
    classes = classificar_c1(df)
    classes.to_csv(destino / "classificacao_c1.csv", index=False)
    salvar_tabela(tabela_descritiva(df), destino, "tab_rq01_04",
                  "Métricas DORA por repositório: mediana e intervalo interquartil (Q1--Q3).",
                  alinhamento="lllrrrr")
    salvar_tabela(tabela_censura(df), destino, "tab_censura",
                  "Casos censurados e releases ignoradas.")
    salvar_tabela(tabela_dora(classes), destino, "tab_dora_c1",
                  "Classificação DORA na combinação de referência (C1).",
                  alinhamento="lrrrrr")
    figura_distribuicoes(df, destino)
    resumo = {rotulo: descrever(df[col] * fator) for rotulo, col, _, fator, _, _ in METRICAS}
    resumo["categorias_c1"] = classes["categoria"].value_counts().to_dict()
    resumo["nao_classificaveis_c1"] = int(classes["categoria"].isna().sum())
    return resumo
