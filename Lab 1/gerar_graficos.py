import sys
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

sns.set_theme(style="whitegrid")

BASE_DIR = Path(__file__).resolve().parent
CSV_PATH_PADRAO = BASE_DIR / "dados_repositorios_github.csv"
OUTPUT_DIR = BASE_DIR / "graficos"
OUTPUT_DIR.mkdir(exist_ok=True)


def carregar_dados(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)

    colunas_esperadas = [
        "nome", "idade_anos", "idade_dias", "contagem_releases",
        "ultima_atualizacao", "prs_aceitas", "linguagem", "estrelas",
        "total_issues", "issues_fechadas", "percentual_issues_fechadas",
        "issues_por_estrela", "tempo_atividade_continuada_dias",
        "proporcao_contribuicoes_externas",
    ]
    faltando = [c for c in colunas_esperadas if c not in df.columns]
    if faltando:
        print(f"Aviso: colunas ausentes no CSV: {faltando}")

    return df


def salvar(fig, nome_arquivo: str):
    caminho = OUTPUT_DIR / nome_arquivo
    fig.savefig(caminho, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Salvo: {caminho}")


def hist_e_boxplot(df, coluna, titulo_geral, titulo_hist, xlabel, cor, nome_arquivo):
    """Gera um par histograma + boxplot lado a lado para uma métrica numérica."""
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    sns.histplot(df[coluna].dropna(), bins=20, kde=True, ax=axes[0], color=cor)
    axes[0].set_title(titulo_hist)
    axes[0].set_xlabel(xlabel)
    axes[0].set_ylabel("Frequência")

    sns.boxplot(y=df[coluna].dropna(), ax=axes[1], color=cor)
    axes[1].set_title(f"Boxplot - {xlabel}")
    axes[1].set_ylabel(xlabel)

    fig.suptitle(titulo_geral, fontsize=13, fontweight="bold")
    fig.tight_layout()
    salvar(fig, nome_arquivo)


def plot_rq01(df):
    hist_e_boxplot(
        df, "idade_anos",
        titulo_geral="RQ01: Sistemas populares são maduros/antigos?",
        titulo_hist="Distribuição da Idade dos Repositórios",
        xlabel="Idade (anos)",
        cor="#4C72B0",
        nome_arquivo="rq01_idade.png",
    )


def plot_rq02(df):
    hist_e_boxplot(
        df, "prs_aceitas",
        titulo_geral="RQ02: Sistemas populares recebem muita contribuição externa?",
        titulo_hist="Distribuição de Pull Requests Aceitas (merged)",
        xlabel="PRs aceitas",
        cor="#55A868",
        nome_arquivo="rq02_prs_aceitas.png",
    )


def plot_rq03(df):
    hist_e_boxplot(
        df, "contagem_releases",
        titulo_geral="RQ03: Sistemas populares lançam releases com frequência?",
        titulo_hist="Distribuição do Total de Releases",
        xlabel="Número de releases",
        cor="#C44E52",
        nome_arquivo="rq03_releases.png",
    )


def plot_rq04(df):
    hist_e_boxplot(
        df, "ultima_atualizacao",
        titulo_geral="RQ04: Sistemas populares são atualizados com frequência?",
        titulo_hist="Distribuição do Tempo desde a Última Atualização",
        xlabel="Dias desde a última atualização",
        cor="#8172B2",
        nome_arquivo="rq04_ultima_atualizacao.png",
    )


def plot_rq05(df):
    contagem = df["linguagem"].value_counts()

    fig, ax = plt.subplots(figsize=(10, max(4, 0.4 * len(contagem))))
    sns.barplot(x=contagem.values, y=contagem.index, ax=ax, palette="viridis")
    ax.set_title(
        "RQ05: Linguagem Primária dos Repositórios Populares",
        fontsize=13, fontweight="bold",
    )
    ax.set_xlabel("Quantidade de repositórios")
    ax.set_ylabel("Linguagem")
    for i, v in enumerate(contagem.values):
        ax.text(v, i, f" {v}", va="center")
    fig.tight_layout()
    salvar(fig, "rq05_linguagens.png")


def plot_rq06(df):
    hist_e_boxplot(
        df, "percentual_issues_fechadas",
        titulo_geral="RQ06: Sistemas populares possuem alto percentual de issues fechadas?",
        titulo_hist="Distribuição do % de Issues Fechadas",
        xlabel="% de issues fechadas",
        cor="#CCB974",
        nome_arquivo="rq06_issues_fechadas.png",
    )


def plot_rq07(df, top_n_linguagens=8):
    top_langs = df["linguagem"].value_counts().nlargest(top_n_linguagens).index
    df_top = df[df["linguagem"].isin(top_langs)].copy()

    metricas = [
        ("prs_aceitas", "PRs Aceitas (RQ02)"),
        ("contagem_releases", "Total de Releases (RQ03)"),
        ("ultima_atualizacao", "Dias desde Última Atualização (RQ04)"),
    ]

    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    for ax, (coluna, titulo) in zip(axes, metricas):
        sns.boxplot(data=df_top, x="linguagem", y=coluna, ax=ax, palette="Set2")
        ax.set_title(titulo)
        ax.set_xlabel("Linguagem")
        ax.set_ylabel(titulo)
        ax.tick_params(axis="x", rotation=45)

    fig.suptitle(
        "RQ07: Linguagens mais populares recebem mais contribuição,\n"
        "lançam mais releases e são atualizadas com mais frequência?",
        fontsize=13, fontweight="bold",
    )
    fig.tight_layout()
    salvar(fig, "rq07_por_linguagem.png")

    resumo = (
        df_top.groupby("linguagem")[
            ["prs_aceitas", "contagem_releases", "ultima_atualizacao"]
        ]
        .agg(["mean", "median"])
        .round(2)
        .sort_values(("prs_aceitas", "mean"), ascending=False)
    )
    resumo_path = OUTPUT_DIR / "rq07_resumo_por_linguagem.csv"
    resumo.to_csv(resumo_path)
    print(f"Resumo estatístico por linguagem salvo em: {resumo_path}")


def plot_rq09(df):
    hist_e_boxplot(
        df, "tempo_atividade_continuada_dias",
        titulo_geral="Tempo Medio de Atividade Continuada",
        titulo_hist="Distribuicao do Tempo entre Criacao e Ultima Atividade",
        xlabel="Tempo de atividade continuada (dias)",
        cor="#64B5CD",
        nome_arquivo="tempo_atividade_continuada.png",
    )


def plot_rq10(df):
    hist_e_boxplot(
        df, "proporcao_contribuicoes_externas",
        titulo_geral="RQ10: Proporcao de Contribuicoes Externas",
        titulo_hist="Distribuicao de PRs Merged por Issue Fechada",
        xlabel="PRs merged / issues fechadas",
        cor="#DD8452",
        nome_arquivo="rq10_proporcao_contribuicoes_externas.png",
    )


def main():
    csv_path = Path(sys.argv[1]) if len(sys.argv) > 1 else CSV_PATH_PADRAO

    if not csv_path.exists():
        print(f"Arquivo não encontrado: {csv_path}")
        print("Rode primeiro o main.py para gerar o CSV, ou informe o caminho correto.")
        return

    df = carregar_dados(csv_path)
    print(f"{len(df)} repositórios carregados de {csv_path}\n")

    plot_rq01(df)
    plot_rq02(df)
    plot_rq03(df)
    plot_rq04(df)
    plot_rq05(df)
    plot_rq06(df)
    plot_rq07(df)
    plot_rq09(df)
    if "proporcao_contribuicoes_externas" in df.columns:
        plot_rq10(df)

    print(f"\nTodos os gráficos foram salvos em: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
