import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats


COR_WELCH = "#2F6DB5"
COR_MW = "#D9772B"
COR_REGIAO = "#C9CDD3"
COR_COM_BOT = "#2A9D8F"
COR_SEM_BOT = "#7A5AA6"


def carregar_dados():
    reais = pd.read_csv("data/prs.csv")
    reais = reais[reais["tempo_merge_horas"] > 0]

    simulados = pd.read_csv("data/simulados.csv")

    with open("data/resultados.json", encoding="utf-8") as arquivo:
        resultados = json.load(arquivo)

    return reais, simulados, resultados


def grafico_g1(reais, simulados):
    todos = pd.concat([
        reais["tempo_merge_horas"],
        simulados["tempo_merge_horas"]
    ])

    faixas = np.logspace(
        np.log10(todos.min()),
        np.log10(todos.max()),
        15
    )

    fig, eixos = plt.subplots(
        2, 2,
        figsize=(10, 6),
        sharex=True,
        sharey=True
    )

    paineis = [
        (eixos[0, 0], reais, "com_bot",
         "Reais: com bot", COR_COM_BOT),

        (eixos[0, 1], reais, "sem_bot",
         "Reais: sem bot", COR_SEM_BOT),

        (eixos[1, 0], simulados, "com_bot",
         "Simulados: com bot", COR_COM_BOT),

        (eixos[1, 1], simulados, "sem_bot",
         "Simulados: sem bot", COR_SEM_BOT)
    ]

    for eixo, dados, grupo, titulo, cor in paineis:
        tempos = dados.loc[
            dados["grupo"] == grupo,
            "tempo_merge_horas"
        ]

        eixo.hist(
            tempos,
            bins=faixas,
            color=cor,
            edgecolor="white",
            label=titulo
        )

        eixo.set_xscale("log")
        eixo.set_title(titulo)
        eixo.legend()

    fig.suptitle(
        "G1: tempo até o merge nos dados reais e simulados"
    )

    fig.supxlabel(
        "Tempo até o merge (horas, escala logarítmica)"
    )

    fig.supylabel("Quantidade de PRs")

    fig.tight_layout()

    return fig


def desenhar_painel(
    eixo,
    x,
    curva,
    critico_baixo,
    critico_alto,
    observado,
    cor,
    nome
):
    centro = (critico_baixo + critico_alto) / 2
    distancia = abs(observado - centro)

    eixo.plot(
        x,
        curva,
        color=cor,
        linewidth=2,
        label=f"Distribuição sob H₀ ({nome})"
    )

    eixo.fill_between(
        x,
        curva,
        where=(
            (x <= critico_baixo) |
            (x >= critico_alto)
        ),
        color=COR_REGIAO,
        label="Região de rejeição"
    )

    eixo.fill_between(
        x,
        curva,
        where=np.abs(x - centro) >= distancia,
        color=cor,
        alpha=0.45,
        label="Área do p-valor"
    )

    eixo.axvline(
        observado,
        color="black",
        linestyle="--",
        label="Valor do exemplo"
    )

    eixo.set_ylabel("Densidade")

    eixo.legend(
        fontsize=8,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.2),
        ncol=2
    )


def grafico_g2(resultados):
    alfa = resultados["alfa"]
    n = resultados["n"]

    fig, (eixo_welch, eixo_mw) = plt.subplots(
        1, 2,
        figsize=(11, 4.5)
    )

    # t de Welch
    gl = resultados["welch_gl"]

    critico = stats.t.ppf(
        1 - alfa / 2,
        gl
    )

    limite = max(
        4,
        abs(resultados["welch_t"]) + 1
    )

    x = np.linspace(-limite, limite, 1000)

    desenhar_painel(
        eixo_welch,
        x,
        stats.t.pdf(x, gl),
        -critico,
        critico,
        resultados["welch_t"],
        COR_WELCH,
        "t de Welch"
    )

    eixo_welch.set_title(
        f"t de Welch (p = {resultados['welch_p']:.3g})"
    )

    eixo_welch.set_xlabel(
        "Estatística t (sem unidade)"
    )

    # Mann-Whitney
    media = n * n / 2

    desvio = np.sqrt(
        n * n * (2 * n + 1) / 12
    )

    critico_u = (
        stats.norm.ppf(1 - alfa / 2) * desvio
    )

    limite_u = max(
        4 * desvio,
        abs(resultados["mw_u"] - media) + desvio
    )

    x_u = np.linspace(
        media - limite_u,
        media + limite_u,
        1000
    )

    desenhar_painel(
        eixo_mw,
        x_u,
        stats.norm.pdf(x_u, media, desvio),
        media - critico_u,
        media + critico_u,
        resultados["mw_u"],
        COR_MW,
        "Mann-Whitney"
    )

    eixo_mw.set_title(
        f"Mann-Whitney (p = {resultados['mw_p']:.3g})"
    )

    eixo_mw.set_xlabel(
        "Estatística U (sem unidade)"
    )

    fig.suptitle(
        "G2: estatística dos testes quando H₀ é verdadeira"
    )

    fig.tight_layout()

    return fig
