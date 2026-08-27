import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent
BASE_DIR = SRC_DIR.parent

if str(SRC_DIR) not in sys.path:
    sys.path.append(str(SRC_DIR))

import pandas as pd
from collectors.repositories import fetch_repositories

from collectors.rq01 import process_rq01
from collectors.rq02 import process_rq02
from collectors.rq03 import process_rq03
from collectors.rq04 import process_rq04
from collectors.rq05 import process_rq05
from collectors.rq06 import process_rq06
from collectors.rq07 import process_rq07
from collectors.rq08ProporçãoDeIssuesEmRelacaoAComunidade import process_rq08
from collectors.rq09 import process_rq09


DEFAULT_SEARCH_QUERY = "science OR machine-learning OR deep-learning OR artificial-intelligence OR data-science OR computer-vision stars:>1000 sort:stars-desc"
DEFAULT_SAMPLE_LIMIT = 1000


def get_search_params():
    if len(sys.argv) > 1:
        search_query = sys.argv[1]
    else:
        search_query = DEFAULT_SEARCH_QUERY

    if len(sys.argv) > 2:
        sample_limit = int(sys.argv[2])
    else:
        sample_limit = DEFAULT_SAMPLE_LIMIT

    return search_query, sample_limit


def main():
    search_query, sample_limit = get_search_params()
    print(f"Iniciando a busca no GitHub com a query: '{search_query}'...")

    repos = fetch_repositories(search_query=search_query, limit=sample_limit)

    if not repos:
        print("Nenhum repositorio retornado.")
        return

    print(f"{len(repos)} repositorios encontrados. Processando metricas...\n")

    lista_dados = []

    for repo in repos:
        name = repo["nameWithOwner"]

        rq01_data = process_rq01(repo["createdAt"])
        prs_aceitas = process_rq02(repo.get("mergedPRs"))
        releasesCount = process_rq03(repo)
        lastUpdate = process_rq04(repo)
        linguagem = process_rq05(repo.get("primaryLanguage"))
        estrelas = process_rq06(repo.get("stargazerCount"))
        issues_data = process_rq07(repo.get("totalIssues"), repo.get("closedIssues"))
        issues_por_estrela = process_rq08(issues_data["total_issues"], estrelas)
        atividade_continuada = process_rq09(
            repo.get("createdAt"), repo.get("pushedAt")
        )

        lista_dados.append({
            "nome": name,
            "idade_anos": rq01_data["idade_anos"],
            "idade_dias": rq01_data["idade_dias"],
            "contagem_releases": releasesCount,
            "ultima_atualizacao": lastUpdate,
            "prs_aceitas": prs_aceitas,
            "linguagem": linguagem,
            "estrelas": estrelas,
            "total_issues": issues_data["total_issues"],
            "issues_fechadas": issues_data["issues_fechadas"],
            "percentual_issues_fechadas": issues_data["percentual_issues_fechadas"],
            "issues_por_estrela": issues_por_estrela,
            "tempo_atividade_continuada_dias": atividade_continuada,
        })

    df = pd.DataFrame(lista_dados)

    print("=" * 60)
    print("RELATORIO FINAL DE ANALISE DAS RQs")
    print("=" * 60)

    print("\n --- RQ 01: Idade dos Repositorios ---")
    print(
        f"Media: {df['idade_anos'].mean():.2f} anos | Mediana:"
        f" {df['idade_anos'].median():.2f} anos"
    )

    print("\n --- RQ 02: PRs Aceitas (Merged) ---")
    print(
        f"Media: {df['prs_aceitas'].mean():.2f} | Mediana:"
        f" {df['prs_aceitas'].median():.0f}"
    )

    print("\n --- RQ 03: Contagem de Releases ---")
    print(
        f"Media: {df['contagem_releases'].mean():.2f} | Mediana:"
        f" {df['contagem_releases'].median():.0f}"
    )

    print("\n --- RQ 04: Ultima Atualizacao ---")
    print(
        f"Media: {df['ultima_atualizacao'].mean():.2f} dias | Mediana:"
        f" {df['ultima_atualizacao'].median():.0f} dias"
    )

    print("\n --- RQ 05: Linguagens Primarias ---")
    print(df["linguagem"].value_counts().to_string())

    print("\n --- RQ 06: Estrelas ---")
    print(
        f"Media: {df['estrelas'].mean():.2f} | Mediana:"
        f" {df['estrelas'].median():.0f}"
    )

    print("\n --- RQ 07 Bonus: Issues ---")
    print(
        f"Total medio de issues: {df['total_issues'].mean():.2f} | "
        f"Issues fechadas em media: {df['percentual_issues_fechadas'].mean():.2f}%"
    )

    print("\n --- RQ 08: Issues por Estrela (Atrito vs Popularidade) ---")
    print(
    f"Media: {df['issues_por_estrela'].mean():.4f} | Mediana:"
    f" {df['issues_por_estrela'].median():.4f}"
    )
    
    print("\n --- RQ 09 Bonus: Tempo de Atividade Continuada ---")
    print(
            f"Media: {df['tempo_atividade_continuada_dias'].mean():.2f} dias | Mediana:"
            f" {df['tempo_atividade_continuada_dias'].median():.0f} dias"
        )

    csv_path = BASE_DIR / "dados_repositorios_github.csv"
    df.to_csv(csv_path, index=False)
    print(f"\n Dados processados e salvos em: {csv_path}")


if __name__ == "__main__":
    main()
