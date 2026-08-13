from pathlib import Path
import os
from dotenv import load_dotenv
import requests

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=BASE_DIR / ".env")

GITHUB_TOKEN = os.getenv("GITHUBTOKEN")
GRAPHQL_URL = "https://api.github.com/graphql"


def run_graphql_query(query: str, variables: dict = None):
    if not GITHUB_TOKEN:
        raise ValueError(
            "TOKEN não foi encontrado!"
        )

    headers = {
        "Authorization": f"bearer {GITHUB_TOKEN}",
        "Content-Type": "application/json",
    }

    payload = {"query": query}
    if variables:
        payload["variables"] = variables

    response = requests.post(GRAPHQL_URL, json=payload, headers=headers)

    if response.status_code == 200:
        data = response.json()
        if "errors" in data:
            print("Erros retornados na resposta GraphQL:")
            for err in data["errors"]:
                print(f"   -> {err.get('message')}")
            return None
        return data.get("data")
    else:
        print(f"Erro HTTP {response.status_code}: {response.text}")
        return None