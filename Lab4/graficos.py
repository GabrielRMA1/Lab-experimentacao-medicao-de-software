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


# ---------------------------------------------------------------------------
# Sprint 2: G3 (erro tipo I) e G4 (curvas de poder)
# ---------------------------------------------------------------------------

TESTES = ("t de Welch", "Mann-Whitney")
CORES_TESTES = {"t de Welch": COR_WELCH, "Mann-Whitney": COR_MW}
MARCADORES = {"t de Welch": "o", "Mann-Whitney": "s"}
COR_GRADE = "#E3E5E8"
COR_REFERENCIA = "#555B63"


def carregar_simulacoes():
    simulacoes = pd.read_csv("data/simulacoes.csv")
    poder_n = pd.read_csv("data/poder_por_n.csv")
    with open("data/reais_resultados.json", encoding="utf-8") as arquivo:
        reais = json.load(arquivo)
    return simulacoes, poder_n, reais


def _estilo_eixo(eixo):
    eixo.grid(axis="y", color=COR_GRADE, linewidth=0.8)
    eixo.set_axisbelow(True)
    for lado in ("top", "right"):
        eixo.spines[lado].set_visible(False)


def grafico_g3(simulacoes, alfa=0.05):
    """Erro tipo I de cada teste em cada situação (redução = 0, ou seja, H0 verdadeira)."""
    h0 = simulacoes[(simulacoes["reducao_mediana"] == 0) & (simulacoes["alfa"] == alfa)]
    situacoes = h0.drop_duplicates("situacao")[["situacao", "nome_situacao"]]
    x = np.arange(len(situacoes))
    largura = 0.36

    fig, eixo = plt.subplots(figsize=(11, 4.8))
    # Faixa de Bradley (0,5α a 1,5α): desvio aceitável em torno do nível nominal
    eixo.axhspan(0.5 * alfa, 1.5 * alfa, color="#F1F2F4", zorder=0,
                 label=f"Faixa aceitável ({0.5 * alfa:.2%} a {1.5 * alfa:.2%}, critério de Bradley)".replace(".", ","))

    for i, teste in enumerate(TESTES):
        dados = h0[h0["teste"] == teste].set_index("situacao").loc[situacoes["situacao"]]
        posicoes = x + (i - 0.5) * largura
        eixo.bar(posicoes, dados["taxa_rejeicao"], width=largura - 0.04,
                 color=CORES_TESTES[teste], label=teste, zorder=2)
        eixo.errorbar(posicoes, dados["taxa_rejeicao"], yerr=1.96 * dados["erro_padrao"],
                      fmt="none", ecolor="#2B2F33", capsize=3, linewidth=1, zorder=3)
        casas = 1 if alfa >= 0.05 else 2
        for px, valor, ep in zip(posicoes, dados["taxa_rejeicao"], dados["erro_padrao"]):
            eixo.text(px, valor + 1.96 * ep + 0.04 * alfa, f"{valor:.{casas}%}".replace(".", ","),
                      ha="center", va="bottom", fontsize=9, color="#2B2F33")

    eixo.axhline(alfa, color=COR_REFERENCIA, linestyle="--", linewidth=1.2,
                 label=f"Nível nominal α = {alfa:.0%}", zorder=1)
    eixo.set_xticks(x)
    eixo.set_xticklabels([f"{s}. {n}".replace(": ", ":\n") for s, n in situacoes.values], fontsize=9)
    eixo.set_ylabel("Taxa de erro tipo I (proporção de p < α)")
    eixo.set_xlabel("Situação simulada (H₀ verdadeira, 10.000 repetições)")
    eixo.yaxis.set_major_formatter(
        plt.FuncFormatter(lambda v, _: f"{v:.{0 if alfa >= 0.05 else 2}%}".replace(".", ",")))
    eixo.set_ylim(0, max(2.2 * alfa, h0["taxa_rejeicao"].max() * 1.3))
    _estilo_eixo(eixo)
    eixo.legend(fontsize=8.5, loc="upper center", ncol=4, frameon=False)
    eixo.set_title(f"G3: erro tipo I dos dois testes em cada situação (α = {alfa})".replace("0.", "0,"))
    fig.tight_layout()
    return fig


def grafico_g4(simulacoes, alfa=0.05):
    """Curvas de poder: proporção de rejeições × tamanho do efeito, uma por situação."""
    dados = simulacoes[simulacoes["alfa"] == alfa]
    situacoes = dados.drop_duplicates("situacao")[["situacao", "nome_situacao", "n"]]

    fig, eixos = plt.subplots(2, 2, figsize=(11, 7.5), sharex=True, sharey=True)
    for eixo, (sid, nome, n) in zip(eixos.flat, situacoes.values):
        finais = {t: dados[(dados["situacao"] == sid) & (dados["teste"] == t)].iloc[-1]["taxa_rejeicao"]
                  for t in TESTES}
        proximos = abs(finais[TESTES[0]] - finais[TESTES[1]]) < 0.05
        for teste in TESTES:
            curva = dados[(dados["situacao"] == sid) & (dados["teste"] == teste)]
            eixo.plot(curva["reducao_mediana"] * 100, curva["taxa_rejeicao"],
                      color=CORES_TESTES[teste], marker=MARCADORES[teste], markersize=6,
                      linewidth=2, label=teste,
                      markeredgecolor="white", markeredgewidth=1)
            ultimo = curva.iloc[-1]
            eixo.annotate(f"{ultimo['taxa_rejeicao']:.0%}", (ultimo["reducao_mediana"] * 100, ultimo["taxa_rejeicao"]),
                          xytext=(6, (6 if finais[teste] >= max(finais.values()) else -6) if proximos else 0),
                          textcoords="offset points", va="center", fontsize=8.5, color="#2B2F33")
        eixo.axhline(alfa, color=COR_REFERENCIA, linestyle="--", linewidth=1)
        eixo.axhline(0.8, color=COR_REFERENCIA, linestyle=":", linewidth=1)
        eixo.set_title(f"{sid}. {nome} (n = {n} por grupo)", fontsize=10)
        eixo.set_ylim(0, 1.02)
        eixo.set_xlim(-3, 98)
        eixo.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
        _estilo_eixo(eixo)

    eixos[0, 0].text(1, 0.8 + 0.015, "80% de poder", fontsize=8, color=COR_REFERENCIA)
    eixos[0, 0].text(1, alfa + 0.015, f"α = {alfa}".replace("0.", "0,"), fontsize=8, color=COR_REFERENCIA)
    alcas, rotulos = eixos[0, 0].get_legend_handles_labels()
    fig.legend(alcas, rotulos, loc="upper center", ncol=2, frameon=False, bbox_to_anchor=(0.5, 0.95))
    fig.suptitle(f"G4: curvas de poder dos dois testes (α = {alfa})".replace("0.", "0,"))
    fig.supxlabel("Tamanho do efeito: redução da mediana do tempo de merge com bot (%)")
    fig.supylabel("Poder (proporção de rejeições de H₀)")
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    return fig


def grafico_poder_por_n(poder_n, razao):
    """Extra: poder para o efeito observado nos dados reais, variando o tamanho da amostra."""
    fig, eixo = plt.subplots(figsize=(9, 4))
    for teste in TESTES:
        curva = poder_n[poder_n["teste"] == teste]
        eixo.plot(curva["n"], curva["poder"], color=CORES_TESTES[teste], marker=MARCADORES[teste],
                  markersize=6, linewidth=2, label=teste, markeredgecolor="white", markeredgewidth=1)
    eixo.axhline(0.8, color=COR_REFERENCIA, linestyle=":", linewidth=1, label="80% de poder")
    eixo.axvline(30, color=COR_REFERENCIA, linestyle="--", linewidth=1, label="n coletado (30)")
    eixo.set_xscale("log")
    eixo.set_xticks(poder_n["n"].unique())
    eixo.get_xaxis().set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0f}"))
    eixo.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
    eixo.set_ylim(0, 1.02)
    eixo.set_xlabel("Tamanho da amostra por grupo (PRs, escala logarítmica)")
    eixo.set_ylabel("Poder (α = 0,05)")
    eixo.set_title(f"Extra: poder para o efeito observado (razão de médias geométricas = {razao:.2f})".replace(".", ","))
    _estilo_eixo(eixo)
    eixo.legend(fontsize=8.5, frameon=False, loc="upper left")
    fig.tight_layout()
    return fig
