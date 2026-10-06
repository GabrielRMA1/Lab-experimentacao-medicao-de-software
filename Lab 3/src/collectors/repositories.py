import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import requests
from dotenv import load_dotenv


# ============================================================
# Configuração
# ============================================================

ROOT = Path(__file__).resolve().parents[3]
load_dotenv(ROOT / ".env")

CACHE_DIR = ROOT / "Lab 3" / "data" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

MAX_WORKERS = 8


def filter_records_by_observation_window(
    records: list[dict[str, Any]],
    date_path: tuple[str, ...],
    observation_start: str | None,
    observation_end: str | None,
) -> list[dict[str, Any]]:
    """Filter collected records by a configured inclusive time window."""

    if bool(observation_start) != bool(observation_end):
        raise ValueError(
            "Configure OBSERVATION_START e OBSERVATION_END juntos."
        )
    if observation_start is None:
        return list(records)

    start = datetime.fromisoformat(observation_start.replace("Z", "+00:00"))
    end = datetime.fromisoformat(observation_end.replace("Z", "+00:00"))
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    if start >= end:
        raise ValueError("OBSERVATION_START deve ser anterior a OBSERVATION_END")

    filtered = []
    for record in records:
        value: Any = record
        for key in date_path:
            value = value.get(key) if isinstance(value, dict) else None
        if not value:
            continue
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        if start <= timestamp <= end:
            filtered.append(record)
    return filtered


# ============================================================
# Cliente GitHub
# ============================================================

class GitHubClient:
    def __init__(self, token: str | None = None):
        self.token = token or os.getenv("GITHUBTOKEN")

        if not self.token:
            raise RuntimeError(
                "Token do GitHub não encontrado. "
                "Verifique GITHUBTOKEN no arquivo .env."
            )

        self.base_url = "https://api.github.com"

        self.headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self.token}",
            "X-GitHub-Api-Version": "2026-03-10",
        }

    def get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> requests.Response:

        url = (
            path
            if path.startswith("https://")
            else f"{self.base_url}{path}"
        )

        while True:
            response = requests.get(
                url,
                headers=self.headers,
                params=params,
                timeout=60,
            )

            if response.status_code in (403, 429):
                remaining = response.headers.get(
                    "X-RateLimit-Remaining"
                )

                if remaining == "0" or response.status_code == 429:
                    reset = response.headers.get(
                        "X-RateLimit-Reset"
                    )

                    if reset:
                        wait_seconds = max(
                            int(reset) - int(time.time()) + 1,
                            1,
                        )
                    else:
                        wait_seconds = 10

                    print(
                        f"Rate limit atingido. "
                        f"Aguardando {wait_seconds}s..."
                    )

                    time.sleep(wait_seconds)
                    continue

            return response

    def get_paginated(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        items_key: str | None = None,
        start_url: str | None = None,
        on_page: Callable[[list[dict[str, Any]], str | None], None] | None = None,
    ) -> list[dict[str, Any]]:

        params = dict(params or {})
        params.setdefault("per_page", 100)

        results: list[dict[str, Any]] = []
        url = start_url or path
        if start_url:
            params = {}

        while url:
            response = self.get(
                url,
                params=params,
            )

            if response.status_code >= 400:
                raise RuntimeError(
                    f"Erro na API do GitHub "
                    f"({response.status_code}): "
                    f"{response.text}"
                )

            data = response.json()

            if isinstance(data, list):
                page_items = data
            elif items_key and isinstance(data, dict) and isinstance(
                data.get(items_key), list
            ):
                page_items = data[items_key]
            elif items_key:
                raise RuntimeError(
                    f"Resposta da API não contém uma lista em '{items_key}'."
                )
            else:
                return data

            results.extend(page_items)

            next_url = None
            link_header = response.headers.get("Link", "")

            for link in link_header.split(","):
                if 'rel="next"' in link:
                    next_url = (
                        link
                        .split(";")[0]
                        .strip()
                        .strip("<>")
                    )
                    break

            if on_page:
                on_page(page_items, next_url)

            url = next_url
            params = {}

        return results


# ============================================================
# Busca de repositórios
# ============================================================

def search_repositories(
    client: GitHubClient,
    query: str,
    target: int = 100,
) -> list[dict[str, Any]]:

    repositories: list[dict[str, Any]] = []
    page = 1

    while len(repositories) < target:
        per_page = min(
            100,
            target - len(repositories),
        )

        response = client.get(
            "/search/repositories",
            params={
                "q": query,
                "sort": "stars",
                "order": "desc",
                "per_page": per_page,
                "page": page,
            },
        )

        if response.status_code >= 400:
            raise RuntimeError(
                f"Erro ao buscar repositórios "
                f"({response.status_code}): "
                f"{response.text}"
            )

        data = response.json()
        items = data.get("items", [])

        if not items:
            break

        repositories.extend(items)

        if len(items) < per_page:
            break

        page += 1

    return repositories[:target]


# ============================================================
# Contributors
# ============================================================

def get_contributor_count(
    client: GitHubClient,
    owner: str,
    repo: str,
) -> int | None:

    try:
        contributors = client.get_paginated(
            f"/repos/{owner}/{repo}/contributors",
            params={
                "anon": "true",
                "per_page": 100,
            },
        )

        return len(contributors)

    except RuntimeError as error:
        error_text = str(error).lower()

        if "contributor list is too large" not in error_text:
            raise

        print(
            f"  {owner}/{repo}: lista de contribuidores "
            f"muito grande. Usando stats/contributors..."
        )

    path = f"/repos/{owner}/{repo}/stats/contributors"

    max_attempts = 6

    for attempt in range(1, max_attempts + 1):
        response = client.get(path)

        if response.status_code == 200:
            data = response.json()

            if isinstance(data, list):
                return len(data)

            return None

        if response.status_code == 202:
            wait_seconds = min(2 ** attempt, 30)

            print(
                f"  {owner}/{repo}: GitHub calculando "
                f"estatísticas "
                f"({attempt}/{max_attempts})..."
            )

            time.sleep(wait_seconds)
            continue

        raise RuntimeError(
            f"Erro ao obter estatísticas de contribuidores "
            f"de {owner}/{repo} "
            f"({response.status_code}): {response.text}"
        )

    return None


# ============================================================
# Idade
# ============================================================

def calculate_age_days(created_at: str) -> int:
    created = datetime.fromisoformat(
        created_at.replace("Z", "+00:00")
    )

    now = datetime.now(timezone.utc)

    return (now - created).days


# ============================================================
# Cache
# ============================================================

def cache_path(full_name: str) -> Path:
    """
    Gera o caminho do cache de um repositório.

    Exemplo:
        torvalds/linux
        ->
        data/cache/torvalds__linux.json
    """

    safe_name = full_name.replace("/", "__")

    return CACHE_DIR / f"{safe_name}.json"


def load_cached_repository(
    full_name: str,
) -> dict[str, Any] | None:

    path = cache_path(full_name)

    if not path.exists():
        return None

    try:
        with path.open(
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)

        return data

    except (json.JSONDecodeError, OSError):
        return None


def save_cached_repository(
    data: dict[str, Any],
) -> None:

    path = cache_path(data["full_name"])

    temporary_path = path.with_suffix(".tmp")

    with temporary_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2,
        )

    temporary_path.replace(path)


def collect_cached_paginated(
    client: GitHubClient,
    full_name: str,
    path: str,
    cache_key: str,
    params: dict[str, Any],
    items_key: str | None = None,
    cache_subkey: str | None = None,
    transform: Callable[[dict[str, Any]], dict[str, Any] | None] | None = None,
) -> list[dict[str, Any]]:
    """Collect pages with atomic per-repository checkpoints and resume."""

    cached_repository = load_cached_repository(full_name) or {
        "full_name": full_name,
    }
    pipeline_cache = cached_repository.get("_pipeline_cache", {})
    if not isinstance(pipeline_cache, dict):
        raise RuntimeError(
            f"Cache de coleta inválido para {full_name}; dados preservados."
        )

    cache_group = pipeline_cache.get(cache_key, {})
    if not isinstance(cache_group, dict):
        raise RuntimeError(
            f"Cache da etapa '{cache_key}' inválido para {full_name}; "
            "dados preservados."
        )

    if cache_subkey is None:
        state = cache_group
    else:
        state = cache_group.get(cache_subkey, {})
        if cache_subkey in cache_group and not isinstance(state, dict):
            raise RuntimeError(
                f"Cache do intervalo inválido para {full_name}; "
                "dados preservados."
            )

    if isinstance(state, dict) and state.get("complete") is True:
        items = state.get("items", [])
        if isinstance(items, list):
            return items

    if not isinstance(state, dict):
        state = {}

    cached_items = state.get("items", [])
    if not isinstance(cached_items, list):
        raise RuntimeError(
            f"Itens em cache inválidos para {full_name}; dados preservados."
        )
    items = list(cached_items)
    start_url = state.get("next_url")

    def save_page(
        page_items: list[dict[str, Any]],
        next_url: str | None,
    ) -> None:
        for item in page_items:
            normalized = transform(item) if transform else item
            if normalized is not None:
                items.append(normalized)

        new_state = {
            "items": items,
            "next_url": next_url,
            "complete": next_url is None,
        }
        if cache_subkey is None:
            pipeline_cache[cache_key] = new_state
        else:
            pipeline_cache[cache_key] = cache_group
            cache_group[cache_subkey] = new_state
        cached_repository["_pipeline_cache"] = pipeline_cache
        save_cached_repository(cached_repository)

    client.get_paginated(
        path,
        params=params,
        items_key=items_key,
        start_url=start_url,
        on_page=save_page,
    )

    return items


# ============================================================
# Metadata de um repositório
# ============================================================

def collect_repository_metadata(
    client: GitHubClient,
    repository: dict[str, Any],
) -> dict[str, Any]:

    full_name = repository["full_name"]

    # --------------------------------------------------------
    # Verifica cache
    # --------------------------------------------------------

    cached = load_cached_repository(full_name)

    if cached is not None:
        return {
            key: value
            for key, value in cached.items()
            if key != "_pipeline_cache"
        }

    owner = repository["owner"]["login"]
    name = repository["name"]

    contributors = get_contributor_count(
        client,
        owner,
        name,
    )

    created_at = repository.get("created_at")

    data = {
        "full_name": full_name,
        "owner": owner,
        "name": name,
        "html_url": repository["html_url"],
        "default_branch": repository.get(
            "default_branch"
        ),
        "language": repository.get("language"),
        "stars": repository.get(
            "stargazers_count",
            0,
        ),
        "forks": repository.get(
            "forks_count",
            0,
        ),
        "created_at": created_at,
        "age_days": (
            calculate_age_days(created_at)
            if created_at
            else None
        ),
        "updated_at": repository.get("updated_at"),
        "contributors": contributors,
        "archived": repository.get(
            "archived",
            False,
        ),
        "fork": repository.get(
            "fork",
            False,
        ),
    }

    # --------------------------------------------------------
    # Salva no cache imediatamente
    # --------------------------------------------------------

    save_cached_repository(data)

    return data


# ============================================================
# Releases publicadas
# ============================================================

def collect_repository_releases(
    client: GitHubClient,
    repository: dict[str, Any],
) -> list[dict[str, Any]]:
    """Coleta releases publicadas preservando a data de publicação.

    ``published_at`` é a data de referência para análises futuras de
    Deployment Frequency. A função não calcula a métrica.
    """

    owner = repository.get("owner") or repository["full_name"].split("/", 1)[0]
    name = repository.get("name") or repository["full_name"].split("/", 1)[1]

    def normalize_release(
        release: dict[str, Any],
    ) -> dict[str, Any] | None:
        if (
            release.get("draft") is not False
            or release.get("prerelease") is not False
        ):
            return None

        return {
            "id": release.get("id"),
            "tag_name": release.get("tag_name"),
            "name": release.get("name"),
            "created_at": release.get("created_at"),
            "published_at": release.get("published_at"),
            "html_url": release.get("html_url"),
            "target_commitish": release.get("target_commitish"),
            "prerelease": release.get("prerelease", False),
            "draft": False,
        }

    return collect_cached_paginated(
        client,
        repository["full_name"],
        f"/repos/{owner}/{name}/releases",
        cache_key="releases",
        params={"per_page": 100},
        transform=normalize_release,
    )


# ============================================================
# Commits entre releases
# ============================================================

def collect_repository_commits(
    client: GitHubClient,
    repository: dict[str, Any],
    since: str,
    until: str,
) -> list[dict[str, Any]]:
    """Coleta commits da branch padrão dentro do intervalo de releases.

    O limite inicial é exclusivo e o final inclusivo. A seleção local usa
    ``commit.author.date``, referência para o cálculo futuro de Lead Time.
    """

    start = datetime.fromisoformat(since.replace("Z", "+00:00"))
    end = datetime.fromisoformat(until.replace("Z", "+00:00"))

    if start >= end:
        raise ValueError("since deve ser anterior a until")

    owner = repository.get("owner") or repository["full_name"].split("/", 1)[0]
    name = repository.get("name") or repository["full_name"].split("/", 1)[1]
    default_branch = repository.get("default_branch")

    if not default_branch:
        raise ValueError(
            f"Branch padrão não informada para {owner}/{name}"
        )

    def normalize_commit(
        item: dict[str, Any],
    ) -> dict[str, Any] | None:
        commit_data = item.get("commit") or {}
        author = commit_data.get("author") or {}
        author_date = author.get("date")

        if not author_date:
            return None

        author_datetime = datetime.fromisoformat(
            author_date.replace("Z", "+00:00")
        )

        if not start < author_datetime <= end:
            return None

        normalized_commit = {
            "author": {"date": author_date},
        }
        committer_date = (commit_data.get("committer") or {}).get("date")
        if committer_date:
            normalized_commit["committer"] = {"date": committer_date}

        return {
            "sha": item.get("sha"),
            "commit": normalized_commit,
        }

    return collect_cached_paginated(
        client,
        repository["full_name"],
        f"/repos/{owner}/{name}/commits",
        cache_key="commits_between_releases",
        cache_subkey=f"{since}|{until}",
        params={
            "sha": default_branch,
            "since": since,
            "until": until,
            "per_page": 100,
        },
        transform=normalize_commit,
    )


# ============================================================
# GitHub Actions workflow runs
# ============================================================

def classify_workflow_run(conclusion: str | None) -> str:
    """Classifica uma run sem calcular métricas DORA."""

    if conclusion == "success":
        return "success"

    if conclusion in {"failure", "timed_out", "startup_failure"}:
        return "failure"

    return "ignored"


def collect_repository_workflow_runs(
    client: GitHubClient,
    repository: dict[str, Any],
) -> list[dict[str, Any]]:
    """Coleta workflow runs de push na branch padrão do repositório."""

    owner = repository.get("owner") or repository["full_name"].split("/", 1)[0]
    name = repository.get("name") or repository["full_name"].split("/", 1)[1]
    default_branch = repository.get("default_branch")

    if not default_branch:
        raise ValueError(
            f"Branch padrão não informada para {owner}/{name}"
        )

    fields = (
        "id",
        "head_sha",
        "head_branch",
        "event",
        "status",
        "conclusion",
        "created_at",
        "updated_at",
        "run_started_at",
    )

    def normalize_run(
        run: dict[str, Any],
    ) -> dict[str, Any] | None:
        if (
            run.get("head_branch") != default_branch
            or run.get("event") != "push"
        ):
            return None

        record = {field: run.get(field) for field in fields}
        record["classification"] = classify_workflow_run(
            run.get("conclusion")
        )
        return record

    return collect_cached_paginated(
        client,
        repository["full_name"],
        f"/repos/{owner}/{name}/actions/runs",
        cache_key="workflow_runs",
        params={
            "branch": default_branch,
            "event": "push",
            "per_page": 100,
        },
        items_key="workflow_runs",
        transform=normalize_run,
    )


# ============================================================
# Coleta concorrente
# ============================================================

def collect_all_repository_metadata(
    client: GitHubClient,
    repositories: list[dict[str, Any]],
    errors: list[dict[str, str]] | None = None,
) -> list[dict[str, Any]]:

    total = len(repositories)

    results: list[dict[str, Any] | None] = [
        None
    ] * total

    print(
        f"\nColetando metadata de {total} repositórios "
        f"com {MAX_WORKERS} workers..."
    )

    with ThreadPoolExecutor(
        max_workers=MAX_WORKERS
    ) as executor:

        future_to_index = {
            executor.submit(
                collect_repository_metadata,
                client,
                repository,
            ): index
            for index, repository in enumerate(
                repositories
            )
        }

        completed = 0

        for future in as_completed(
            future_to_index
        ):
            index = future_to_index[future]

            repository = repositories[index]
            full_name = repository["full_name"]

            try:
                results[index] = future.result()

                completed += 1

                print(
                    f"[{completed}/{total}] "
                    f"{full_name}"
                )

            except Exception as error:
                if errors is not None:
                    errors.append(
                        {
                            "repository": full_name,
                            "stage": "metadata",
                            "error": f"{type(error).__name__}: {error}",
                        }
                    )
                print(
                    f"[ERRO] {full_name} (metadata): "
                    f"{type(error).__name__}: {error}"
                )

    return [
        result
        for result in results
        if result is not None
    ]


# ============================================================
# Funil inicial
# ============================================================

def build_initial_funnel(
    candidates: list[dict[str, Any]],
    metadata: list[dict[str, Any]],
    sample_target: int = 100,
    observation_start: str | None = None,
    observation_end: str | None = None,
) -> dict[str, Any]:
    if sample_target < 0:
        raise ValueError("sample_target não pode ser negativo")
    if bool(observation_start) != bool(observation_end):
        raise ValueError(
            "Configure OBSERVATION_START e OBSERVATION_END juntos."
        )

    window_configured = observation_start is not None
    window = {
        "required_months": 12,
        "start": observation_start,
        "end": observation_end,
        "configured": window_configured,
        "status": "configured" if window_configured else "not_configured",
        "note": (
            "A janela oficial ainda não foi configurada; os limites de "
            "data não foram aplicados. Configure OBSERVATION_START e "
            "OBSERVATION_END com as datas fornecidas pelo professor."
            if not window_configured
            else None
        ),
    }

    def in_observation_window(value: str | None) -> bool:
        if not window_configured:
            return True
        if not value:
            return False
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        start = datetime.fromisoformat(observation_start.replace("Z", "+00:00"))
        end = datetime.fromisoformat(observation_end.replace("Z", "+00:00"))
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        return start <= timestamp <= end

    candidate_names = [
        repository.get("full_name") for repository in candidates
    ]
    candidate_name_set = set(candidate_names)
    candidate_metadata = [
        repository
        for repository in metadata
        if repository.get("full_name") in candidate_name_set
    ]
    eligible_actions = []
    discarded_actions = {"metadata_missing": 0, "no_valid_workflow_runs": 0}
    metadata_by_name = {
        repository.get("full_name"): repository
        for repository in candidate_metadata
    }
    for name in candidate_names:
        repository = metadata_by_name.get(name)
        if repository is None:
            discarded_actions["metadata_missing"] += 1
            continue
        valid_runs = [
            run
            for run in repository.get("workflow_runs", [])
            if run.get("head_branch") == repository.get("default_branch")
            and run.get("event") == "push"
            if in_observation_window(run.get("created_at"))
        ]
        if not valid_runs:
            discarded_actions["no_valid_workflow_runs"] += 1
            continue
        eligible_actions.append((repository, valid_runs))

    eligible_minimum = []
    discarded_minimum = {"fewer_than_5_releases": 0, "fewer_than_50_workflow_runs": 0}
    for repository, valid_runs in eligible_actions:
        valid_releases = [
            release
            for release in repository.get("releases", [])
            if release.get("draft") is False
            and release.get("prerelease") is False
            and in_observation_window(release.get("published_at"))
        ]
        missing_releases = len(valid_releases) < 5
        missing_runs = len(valid_runs) < 50
        if missing_releases:
            discarded_minimum["fewer_than_5_releases"] += 1
        if missing_runs:
            discarded_minimum["fewer_than_50_workflow_runs"] += 1
        if not missing_releases and not missing_runs:
            eligible_minimum.append(repository)

    final_repositories = eligible_minimum[:sample_target]
    candidate_stage = {
        "count": len(candidates),
        "reason_for_exclusion": None,
    }
    actions_stage = {
        "count": len(eligible_actions),
        "discarded": sum(discarded_actions.values()),
        "discarded_by_reason": discarded_actions,
        "reason_for_exclusion": "Sem metadados ou sem workflow runs válidos.",
    }
    minimum_stage = {
        "count": len(eligible_minimum),
        "discarded": len(eligible_actions) - len(eligible_minimum),
        "discarded_by_reason": discarded_minimum,
        "minimum_releases": 5,
        "minimum_workflow_runs": 50,
        "reason_for_exclusion": "Menos de 5 releases ou 50 workflow runs.",
    }
    final_stage = {
        "count": len(final_repositories),
        "target": sample_target,
        "discarded": len(eligible_minimum) - len(final_repositories),
        "repository_names": [
            repository.get("full_name") for repository in final_repositories
        ],
        "reason_for_exclusion": "Amostra limitada ao alvo configurado para S01.",
    }
    stages = [
        {"name": "candidates", **candidate_stage},
        {
            "name": "metadata_collected",
            "count": len(candidate_metadata),
            "reason_for_exclusion": None,
        },
        {"name": "with_actions", **actions_stage},
        {"name": "minimum_releases_and_runs", **minimum_stage},
        {"name": "final_sample", **final_stage},
    ]

    return {
        "candidates_found": len(candidates),
        "metadata_collected": len(candidate_metadata),
        "observation_window": window,
        "candidates": candidate_stage,
        "with_actions": actions_stage,
        "minimum_releases_and_runs": minimum_stage,
        "final_sample": final_stage,
        "stages": stages,
    }
