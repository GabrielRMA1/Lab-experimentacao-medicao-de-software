"""Funções comuns das análises (Sprint 03): leitura do CSV, estatística
descritiva (mediana e IQR), tabelas em LaTeX/CSV e figuras.

Toda análise roda **só a partir do CSV** (``data/dataset/dataset_repos.csv``):
nenhuma chamada à API do GitHub.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

import matplotlib

matplotlib.use("Agg")  # gera arquivos sem abrir janela
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]  # pasta "Lab 3"
DATASET_PADRAO = ROOT / "data" / "dataset" / "dataset_repos.csv"
SAIDA_PADRAO = ROOT / "data" / "resultados"
VALIDACAO_PADRAO = ROOT / "data" / "validacao"

HORAS_POR_DIA = 24.0

# Paleta (validada para daltonismo; ver docs): azul e laranja para séries,
# cinza para a referência, rampa azul ordinal para níveis/magnitudes.
AZUL, LARANJA = "#2a78d6", "#eb6834"
CINZA_REF = "#8a8984"
TINTA, TINTA_2, GRADE = "#0b0b0b", "#52514e", "#e4e3df"
RAMPA_ORDINAL = ["#86b6ef", "#3987e5", "#1c5cab", "#0d366b"]  # fraco -> forte

plt.rcParams.update({
    "font.size": 9, "axes.titlesize": 10, "axes.labelsize": 9,
    "axes.edgecolor": TINTA_2, "axes.labelcolor": TINTA, "text.color": TINTA,
    "xtick.color": TINTA_2, "ytick.color": TINTA_2,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": False, "grid.color": GRADE, "grid.linewidth": 0.8,
    "figure.facecolor": "white", "axes.facecolor": "white",
})


def carregar_dataset(caminho: Path = DATASET_PADRAO) -> pd.DataFrame:
    if not Path(caminho).exists():
        raise FileNotFoundError(
            f"{caminho} não existe. Rode a coleta e `python -m src.pipeline consolidate`."
        )
    df = pd.read_csv(caminho)
    if df.empty:
        raise ValueError(f"{caminho} está vazio.")
    return df


def descrever(valores: Iterable[float]) -> dict[str, float | int | None]:
    """n, Q1, mediana e Q3 (quartis com interpolação linear, padrão do pandas)."""

    serie = pd.Series(list(valores), dtype="float64").dropna()
    if serie.empty:
        return {"n": 0, "q1": None, "mediana": None, "q3": None}
    return {
        "n": int(serie.size),
        "q1": float(serie.quantile(0.25)),
        "mediana": float(serie.median()),
        "q3": float(serie.quantile(0.75)),
    }


def fmt(valor: Any, casas: int = 2) -> str:
    """Número no formato brasileiro (vírgula decimal); vazio vira travessão."""

    if valor is None or (isinstance(valor, float) and np.isnan(valor)):
        return "--"
    if isinstance(valor, (int, np.integer)):
        return f"{int(valor):,}".replace(",", ".")
    return f"{float(valor):,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_p(p: float | None) -> str:
    if p is None or np.isnan(p):
        return "--"
    return "< 0,001" if p < 0.001 else fmt(p, 3)


def _tex(texto: Any) -> str:
    s = str(texto)
    for a, b in (("\\", r"\textbackslash{}"), ("&", r"\&"), ("%", r"\%"),
                 ("_", r"\_"), ("#", r"\#"), ("$", r"\$")):
        s = s.replace(a, b)
    for a, b in (("ρ", r"$\rho$"), ("ε²", r"$\varepsilon^2$"), ("ε", r"$\varepsilon$"),
                 ("δ", r"$\delta$"), ("²", r"$^2$"), ("×", r"$\times$"), ("≥", r"$\geq$"),
                 ("≤", r"$\leq$"), ("–", "--")):
        s = s.replace(a, b)
    return s


def salvar_tabela(
    linhas: list[dict[str, Any]],
    destino: Path,
    nome: str,
    legenda: str,
    colunas: list[str] | None = None,
    alinhamento: str | None = None,
) -> None:
    """Grava ``<nome>.csv`` (dados brutos) e ``<nome>.tex`` (tabela do artigo).

    ``linhas`` já devem vir com os textos formatados para o .tex; o .csv
    recebe exatamente os mesmos valores.
    """

    destino.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(linhas, columns=colunas)
    frame.to_csv(destino / f"{nome}.csv", index=False, encoding="utf-8")
    cols = list(frame.columns)
    align = alinhamento or ("l" + "r" * (len(cols) - 1))
    corpo = [
        r"\begin{table}[ht]",
        r"\centering",
        rf"\caption{{{legenda}}}",
        rf"\label{{tab:{nome}}}",
        r"\footnotesize",
        r"\begin{adjustbox}{max width=\linewidth}",
        rf"\begin{{tabular}}{{{align}}}",
        r"\hline",
        " & ".join(rf"\textbf{{{_tex(c)}}}" for c in cols) + r" \\",
        r"\hline",
    ]
    for _, row in frame.iterrows():
        corpo.append(" & ".join(_tex(row[c]) for c in cols) + r" \\")
    corpo += [r"\hline", r"\end{tabular}", r"\end{adjustbox}", r"\end{table}", ""]
    (destino / f"{nome}.tex").write_text("\n".join(corpo), encoding="utf-8")


def salvar_figura(fig: plt.Figure, destino: Path, nome: str, ajustar: bool = True) -> Path:
    pasta = destino / "figuras"
    pasta.mkdir(parents=True, exist_ok=True)
    caminho = pasta / f"{nome}.png"
    if ajustar:
        fig.tight_layout()
    fig.savefig(caminho, dpi=200)
    plt.close(fig)
    return caminho


def eixo_log(eixo: Any, qual: str = "y") -> None:
    """Escala log com rótulos legíveis (0,1 · 1 · 10 · 100), sem rótulos menores."""

    from matplotlib.ticker import FuncFormatter, LogLocator, NullFormatter

    rotulo = FuncFormatter(lambda v, _: f"{v:g}".replace(".", ","))
    alvo = eixo.yaxis if qual == "y" else eixo.xaxis
    (eixo.set_yscale if qual == "y" else eixo.set_xscale)("log")
    alvo.set_major_locator(LogLocator(base=10, subs=(1.0, 2.0, 5.0)))
    alvo.set_major_formatter(rotulo)
    alvo.set_minor_formatter(NullFormatter())


def semanas_da_janela(df: pd.DataFrame) -> float:
    """Semanas da janela, recuperadas do próprio CSV (n_releases ÷ frequência)."""

    validos = df[(df["n_releases"] > 0) & (df["deploy_freq_semana"] > 0)]
    if validos.empty:
        return 365.25 / 7
    return float((validos["n_releases"] / validos["deploy_freq_semana"]).median())
