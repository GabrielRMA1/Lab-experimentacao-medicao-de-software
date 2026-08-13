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

def main():
    SEARCH_QUERY = "stars:>1000 sort:stars-desc"
    print(f"Iniciando a busca no GitHub com a query: '{SEARCH_QUERY}'...")

    repos = fetch_repositories(search_query=SEARCH_QUERY, limit=100)

    if not repos:
        print("Nenhum repositório retornado.")
        return

    print(f"{len(repos)} repositórios encontrados. Processando métricas...\n")

    lista_dados = []

    for repo in repos:
        name = repo["nameWithOwner"]

        rq01_data = process_rq01(repo["createdAt"])
        prs_aceitas = process_rq02(repo.get("mergedPRs"))


        lista_dados.append({
            "nome": name,
            "idade_anos": rq01_data["idade_anos"],
            "idade_dias": rq01_data["idade_dias"],
            "prs_aceitas": prs_aceitas,
        })

    df = pd.DataFrame(lista_dados)

    print("=" * 60)
    print("RELATÓRIO FINAL DE ANÁLISE DAS RQs")
    print("=" * 60)



    print("\n --- RQ 01: Idade dos Repositórios ---")
    print(
        f"Média: {df['idade_anos'].mean():.2f} anos | Mediana:"
        f" {df['idade_anos'].median():.2f} anos"
    )

    print("\n --- RQ 02: PRs Aceitas (Merged) ---")
    print(
        f"Média: {df['prs_aceitas'].mean():.2f} | Mediana:"
        f" {df['prs_aceitas'].median():.0f}"
    )



    csv_path = BASE_DIR / "dados_repositorios_github.csv"
    df.to_csv(csv_path, index=False)
    print(f"\n Dados processados e salvos em: {csv_path}")


if __name__ == "__main__":
    main()