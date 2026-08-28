from pathlib import Path
import os
import time
from dotenv import load_dotenv
import requests

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=BASE_DIR / ".env")

GITHUB_TOKEN = os.getenv("GITHUBTOKEN")
GRAPHQL_URL = "https://api.github.com/graphql"
REQUEST_TIMEOUT = 30
MAX_RETRY_DELAY = 60
RETRYABLE_STATUS_CODES = {429, 502, 503, 504}


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

    retry_attempt = 0
    # while True:
    while retry_attempt < 5:
        try:
            response = requests.post(
                GRAPHQL_URL,
                json=payload,
                headers=headers,
                timeout=REQUEST_TIMEOUT,
            )
        except requests.RequestException as error:
            wait_seconds = min(2**retry_attempt, MAX_RETRY_DELAY)
            print(
                f"Falha de conexao ({error}). Nova tentativa em "
                f"{wait_seconds}s..."
            )
            time.sleep(wait_seconds)
            retry_attempt += 1
            continue

        if response.status_code in RETRYABLE_STATUS_CODES:
            retry_after = response.headers.get("Retry-After")
            try:
                wait_seconds = (
                    max(float(retry_after), 0)
                    if retry_after
                    else 2**retry_attempt
                )
            except ValueError:
                wait_seconds = 2**retry_attempt

            wait_seconds = min(wait_seconds, MAX_RETRY_DELAY)

            print(
                f"Erro HTTP {response.status_code}. Nova tentativa em "
                f"{wait_seconds:g}s..."
            )
            time.sleep(wait_seconds)
            retry_attempt += 1
            continue

        break

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