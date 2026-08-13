import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent
BASE_DIR = SRC_DIR.parent

if str(SRC_DIR) not in sys.path:
    sys.path.append(str(SRC_DIR))

import pandas as pd
from collectors.repositories import fetch_repositories


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


        lista_dados.append({
        })

    df = pd.DataFrame(lista_dados)

    print("=" * 60)
    print("RELATÓRIO FINAL DE ANÁLISE DAS RQs")
    print("=" * 60)


    csv_path = BASE_DIR / "dados_repositorios_github.csv"
    df.to_csv(csv_path, index=False)
    print(f"\n Dados processados e salvos em: {csv_path}")


if __name__ == "__main__":
    main()