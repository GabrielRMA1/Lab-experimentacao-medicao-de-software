"""RQ 06: características dos repositórios × métricas DORA.

Fatores (no mínimo três, enunciado): linguagem principal (5 mais comuns +
"Outras"), quartis de estrelas, quartis de contribuidores, quartis de idade
e, se o consenso da amostra-ouro existir, tipo do projeto (só os 60
repositórios rotulados).

Para cada fator × métrica (RQ 01–04, variantes de referência):
* > 2 grupos: Kruskal-Wallis, tamanho de efeito ε² = H / (n − 1);
* 2 grupos: Mann-Whitney, Cliff's δ = 2·U₁ / (n₁·n₂) − 1;
* p-valores corrigidos por Holm sobre **todos** os testes.

Grupos com menos de ``MIN_POR_GRUPO`` repositórios são deixados de fora do
teste (informado na tabela).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import kruskal, mannwhitneyu
from statsmodels.stats.multitest import multipletests

from src.analise.comum import descrever, fmt, fmt_p, salvar_tabela

MIN_POR_GRUPO = 5
N_LINGUAGENS = 5

METRICAS = [
    ("Deployment frequency", "deploy_freq_semana"),
    ("Lead time (a)", "lt_release_mediana_h"),
    ("CFR (a)", "cfr_ci"),
    ("Recuperação", "rec_mediana_h"),
]

TIPOS = {
    "biblioteca_framework": "Biblioteca/framework",
    "aplicacao_servico": "Aplicação/serviço",
    "ferramenta_cli": "Ferramenta CLI",
    "outro": "Outro",
}


def magnitude_cliff(delta: float) -> str:
    """Romano et al. (2006)."""

    a = abs(delta)
    return ("desprezível" if a < 0.147 else "pequeno" if a < 0.33
            else "médio" if a < 0.474 else "grande")


def magnitude_epsilon(eps: float) -> str:
    """Faixas usuais para ε² (Rea & Parker): < 0,01 desprezível; < 0,08
    pequeno; < 0,26 médio; >= 0,26 grande."""

    return ("desprezível" if eps < 0.01 else "pequeno" if eps < 0.08
            else "médio" if eps < 0.26 else "grande")


def quartis(serie: pd.Series) -> pd.Series:
    rotulos = ["Q1 (menor)", "Q2", "Q3", "Q4 (maior)"]
    try:
        return pd.qcut(serie, 4, labels=rotulos)
    except ValueError:  # muitos empates: menos de 4 faixas distintas
        return pd.qcut(serie.rank(method="first"), 4, labels=rotulos)


def montar_fatores(df: pd.DataFrame, validacao_dir: Path | None) -> dict[str, pd.Series]:
    linguagem = df["language"].fillna("Não informada")
    top = linguagem.value_counts().head(N_LINGUAGENS).index
    fatores = {
        "Linguagem": linguagem.where(linguagem.isin(top), "Outras"),
        "Estrelas (quartis)": quartis(df["stars"]),
        "Contribuidores (quartis)": quartis(df["contributors"]),
        "Idade (quartis)": quartis(df["idade_dias_fim_janela"]),
    }
    consenso = (validacao_dir / "consenso_repos.csv") if validacao_dir else None
    if consenso is not None and consenso.exists():
        rotulos = pd.read_csv(consenso)
        if "tipo_projeto" in rotulos:
            mapa = dict(zip(rotulos["full_name"], rotulos["tipo_projeto"]))
            tipo = df["full_name"].map(mapa).map(TIPOS)
            if tipo.notna().sum() >= 2 * MIN_POR_GRUPO:
                fatores["Tipo do projeto (amostra-ouro)"] = tipo
    return fatores


def testar(valores: pd.Series, grupos: pd.Series) -> dict[str, Any] | None:
    dados = pd.DataFrame({"v": valores, "g": grupos}).dropna()
    contagem = dados["g"].value_counts()
    validos = contagem[contagem >= MIN_POR_GRUPO].index
    dados = dados[dados["g"].isin(validos)]
    amostras = [dados.loc[dados["g"] == g, "v"].to_numpy() for g in validos]
    excluidos = int(contagem[contagem < MIN_POR_GRUPO].sum())
    if len(amostras) < 2:
        return None
    n = len(dados)
    if len(amostras) == 2:
        x, y = amostras
        u, p = mannwhitneyu(x, y, alternative="two-sided")
        delta = 2 * u / (len(x) * len(y)) - 1
        return {"teste": "Mann-Whitney", "estatistica": float(u), "p": float(p),
                "efeito": f"δ = {fmt(delta, 3)}", "magnitude": magnitude_cliff(delta),
                "n": n, "k": 2, "excluidos": excluidos}
    if dados["v"].nunique() < 2:
        return None
    h, p = kruskal(*amostras)
    eps = h / (n - 1)
    return {"teste": "Kruskal-Wallis", "estatistica": float(h), "p": float(p),
            "efeito": f"ε² = {fmt(eps, 3)}", "magnitude": magnitude_epsilon(eps),
            "n": n, "k": len(amostras), "excluidos": excluidos}


def executar(df: pd.DataFrame, destino: Path, validacao_dir: Path | None = None) -> list[dict[str, Any]]:
    fatores = montar_fatores(df, validacao_dir)
    testes, medianas = [], []
    for nome_fator, grupos in fatores.items():
        for rotulo, coluna in METRICAS:
            r = testar(df[coluna], grupos)
            if r is not None:
                testes.append({"fator": nome_fator, "metrica": rotulo, **r})
            for grupo in sorted(grupos.dropna().unique(), key=str):
                d = descrever(df.loc[grupos == grupo, coluna])
                medianas.append({"Fator": nome_fator, "Grupo": grupo, "Métrica": rotulo,
                                 "n": d["n"], "Q1": d["q1"], "Mediana": d["mediana"], "Q3": d["q3"]})

    if testes:
        _, p_holm, _, _ = multipletests([t["p"] for t in testes], method="holm")
        for t, ph in zip(testes, p_holm):
            t["p_holm"] = float(ph)
            t["significativo"] = ph < 0.05

    salvar_tabela(
        [{"Fator": t["fator"], "Métrica": t["metrica"], "Teste": t["teste"],
          "Estatística": fmt(t["estatistica"], 2), "p": fmt_p(t["p"]),
          "p (Holm)": fmt_p(t["p_holm"]), "Efeito": t["efeito"],
          "Magnitude": t["magnitude"], "n": fmt(t["n"])} for t in testes],
        destino, "tab_rq06",
        f"Testes por fator e métrica, com correção de Holm ({len(testes)} testes) e tamanho de efeito.",
        alinhamento="llllrrrllr",
    )
    pd.DataFrame(medianas).to_csv(destino / "rq06_medianas_por_grupo.csv", index=False)
    if testes:
        figura(testes, destino)
    return testes


MAGNITUDES = ["desprezível", "pequeno", "médio", "grande"]


def figura(testes: list[dict[str, Any]], destino: Path) -> None:
    """Mapa de calor fator × métrica: cor = magnitude do efeito, * = Holm < 0,05."""

    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap
    from matplotlib.patches import Patch

    from src.analise.comum import RAMPA_ORDINAL, TINTA, salvar_figura

    fatores = list(dict.fromkeys(t["fator"] for t in testes))
    metricas = [rotulo for rotulo, _ in METRICAS]
    grade = np.full((len(fatores), len(metricas)), np.nan)
    textos = [["" for _ in metricas] for _ in fatores]
    for t in testes:
        i, j = fatores.index(t["fator"]), metricas.index(t["metrica"])
        grade[i, j] = MAGNITUDES.index(t["magnitude"])
        textos[i][j] = t["efeito"].split(" = ")[1] + (" *" if t["significativo"] else "")

    fig, eixo = plt.subplots(figsize=(7.5, 0.55 * len(fatores) + 1.6))
    mapa = ListedColormap(RAMPA_ORDINAL).with_extremes(bad="#f1f0ec")
    eixo.imshow(np.ma.masked_invalid(grade), cmap=mapa, vmin=-0.5, vmax=3.5, aspect="auto")
    for i in range(len(fatores)):
        for j in range(len(metricas)):
            if textos[i][j]:
                escuro = grade[i, j] >= 2
                eixo.text(j, i, textos[i][j], ha="center", va="center", fontsize=8.5,
                          color="white" if escuro else TINTA,
                          fontweight="bold" if textos[i][j].endswith("*") else "normal")
    eixo.set_xticks(range(len(metricas)), metricas)
    eixo.set_yticks(range(len(fatores)), fatores)
    eixo.tick_params(length=0)
    eixo.set_xticks(np.arange(-0.5, len(metricas)), minor=True)
    eixo.set_yticks(np.arange(-0.5, len(fatores)), minor=True)
    eixo.grid(which="minor", color="white", linewidth=2)
    for lado in eixo.spines.values():
        lado.set_visible(False)
    eixo.set_title("RQ 06 · Tamanho de efeito por fator e métrica", loc="left")
    legenda = [Patch(facecolor=c, label=m) for c, m in zip(RAMPA_ORDINAL, MAGNITUDES)]
    eixo.legend(handles=legenda, title="Magnitude do efeito", fontsize=8, title_fontsize=8,
                loc="upper left", bbox_to_anchor=(1.01, 1), frameon=False)
    fig.text(0.01, 0.01, "Valor na célula: ε² (Kruskal-Wallis) ou δ (Mann-Whitney). "
             "* = significativo após correção de Holm (p < 0,05).", fontsize=7.5, color="#52514e")
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    salvar_figura(fig, destino, "rq06_efeitos", ajustar=False)
