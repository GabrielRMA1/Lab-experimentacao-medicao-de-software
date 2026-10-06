from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Permite executar `python src/main.py` diretamente.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.collectors.repositories import (  # noqa: E402
    GitHubClient,
    build_initial_funnel,
    collect_all_repository_metadata,
    collect_repository_commits,
    collect_repository_releases,
    collect_repository_workflow_runs,
    filter_records_by_observation_window,
    search_repositories,
)


DATA_DIR = ROOT / "data"


def save_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def record_collection_error(
    errors: list[dict[str, str]],
    repository: dict[str, object],
    stage: str,
    error: Exception,
    interval: dict[str, str] | None = None,
) -> None:
    record = {
        "repository": str(repository.get("full_name", "unknown")),
        "stage": stage,
        "error": f"{type(error).__name__}: {error}",
    }
    if interval:
        record["interval"] = f"{interval['since']}..{interval['until']}"
    errors.append(record)
    print(
        f"[ERRO] {record['repository']} ({stage}): {record['error']}"
    )


def main() -> None:
    query = os.getenv("GITHUB_REPO_QUERY", "stars:>1000")
    target = int(os.getenv("REPO_TARGET", "100"))
    sample_target = int(os.getenv("S01_SAMPLE_TARGET", "100"))
    observation_start = os.getenv("OBSERVATION_START")
    observation_end = os.getenv("OBSERVATION_END")

    print(f"Buscando até {target} repositórios...")
    print(f"Consulta: {query}")

    client = GitHubClient()
    candidates = search_repositories(client, query=query, target=target)

    collection_errors: list[dict[str, str]] = []
    metadata = collect_all_repository_metadata(
        client,
        candidates,
        errors=collection_errors,
    )

    for repository_data in metadata:
        try:
            repository_data["releases"] = filter_records_by_observation_window(
                collect_repository_releases(client, repository_data),
                ("published_at",),
                observation_start,
                observation_end,
            )
        except Exception as error:
            record_collection_error(
                collection_errors,
                repository_data,
                "releases",
                error,
            )
            repository_data["releases"] = []

        try:
            repository_data["workflow_runs"] = filter_records_by_observation_window(
                collect_repository_workflow_runs(client, repository_data),
                ("created_at",),
                observation_start,
                observation_end,
            )
        except Exception as error:
            record_collection_error(
                collection_errors,
                repository_data,
                "workflow_runs",
                error,
            )
            repository_data["workflow_runs"] = []

    funnel = build_initial_funnel(
        candidates,
        metadata,
        sample_target=sample_target,
        observation_start=observation_start,
        observation_end=observation_end,
    )
    funnel["collection_errors"] = collection_errors
    final_names = set(funnel["final_sample"]["repository_names"])
    final_sample = [
        repository
        for repository in metadata
        if repository.get("full_name") in final_names
    ]

    for repository_data in final_sample:
        ordered_releases = sorted(
            (
                release
                for release in repository_data.get("releases", [])
                if release.get("published_at")
            ),
            key=lambda release: release["published_at"],
        )
        repository_data["commits_between_releases"] = []

        for previous_release, current_release in zip(
            ordered_releases,
            ordered_releases[1:],
        ):
            interval = {
                "since": previous_release["published_at"],
                "until": current_release["published_at"],
            }
            try:
                commits = filter_records_by_observation_window(
                    collect_repository_commits(
                        client,
                        repository_data,
                        since=interval["since"],
                        until=interval["until"],
                    ),
                    ("commit", "author", "date"),
                    observation_start,
                    observation_end,
                )
            except Exception as error:
                record_collection_error(
                    collection_errors,
                    repository_data,
                    "commits_between_releases",
                    error,
                    interval=interval,
                )
                commits = []
            repository_data["commits_between_releases"].append(
                {
                    "from_release": previous_release.get("tag_name"),
                    "to_release": current_release.get("tag_name"),
                    **interval,
                    "commits": commits,
                }
            )

    save_json(DATA_DIR / "repositories.json", final_sample)
    save_json(DATA_DIR / "funnel.json", funnel)

    print()
    print(
        f"Concluído: {len(final_sample)} repositórios na amostra final "
        f"da S01 (alvo: {sample_target})."
    )
    print(f"Dados: {DATA_DIR / 'repositories.json'}")
    print(f"Funil: {DATA_DIR / 'funnel.json'}")


if __name__ == "__main__":
    main()
