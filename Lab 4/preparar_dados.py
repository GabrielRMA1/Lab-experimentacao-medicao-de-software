import json
import pandas as pd

NOME_DO_BOT = "coderabbitai"


def carregar(caminho):
    with open(caminho, encoding="utf-8-sig") as arquivo:
        return json.load(arquivo)


def montar_linhas(prs, grupo):
    linhas = []
    for pr in prs:
        if pr["author"] and pr["author"].get("is_bot"):
            continue

        revisores = [r["author"]["login"] for r in pr["reviews"] if r["author"]]
        bot_revisou = NOME_DO_BOT in revisores
        if bot_revisou != (grupo == "com_bot"):
            continue

        inicio = pd.Timestamp(pr["createdAt"])
        fim = pd.Timestamp(pr["mergedAt"])
        horas = (fim - inicio).total_seconds() / 3600
        linhas.append({"pr": pr["number"], "grupo": grupo, "tempo_merge_horas": round(horas, 2)})
    return linhas


linhas = montar_linhas(carregar("data/prs_antes.json"), "sem_bot")
linhas += montar_linhas(carregar("data/prs_depois.json"), "com_bot")

dados = pd.DataFrame(linhas)
print("PRs disponíveis:")
print(dados["grupo"].value_counts())

amostra = dados.groupby("grupo").sample(n=30, random_state=42)
amostra.to_csv("data/prs.csv", index=False)
print("Arquivo data/prs.csv criado com", len(amostra), "PRs.")