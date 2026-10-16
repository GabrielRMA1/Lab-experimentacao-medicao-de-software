"""Coleta dos commits de cada release via ``compare`` (S02 — RQ 02 e RQ 03b).

Por que ``compare`` e não ``GET /commits?since=&until=``?

* O endpoint de commits filtra por data de *committer*; já o lead time usa a
  data de *autor* do commit. Um commit escrito em janeiro e mergeado em março
  tem ``author.date`` anterior à release anterior — se o intervalo for
  filtrado por data de autor (como na S01), ele some e o lead time (a) fica
  subestimado.
* ``compare/{anterior}...{R}`` devolve exatamente os commits que entraram em
  R e não estavam na release anterior, que é a definição do enunciado.

Cada resposta é guardada em ``_pipeline_cache["compare_v1"]`` (uma entrada por
par de releases), com a mesma lógica de checkpoint/retomada das demais etapas.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote

from src.collectors.repositories import (
    GitHubClient,
    collect_cached_paginated,
    load_cached_repository,
    save_cached_repository,
)
from src.metricas.lead_time import make_compare_key, parse_iso

CACHE_KEY = "compare_v1"
_NOT_FOUND_CODES = ("(404)", "(422)")


def normalize_compare_commit(item: dict[str, Any]) -> dict[str, Any]:
    """Reduz um commit do ``compare`` ao que as métricas precisam."""

    commit = item.get("commit") or {}
    author_date = (commit.get("author") or {}).get("date")
    committer_date = (commit.get("committer") or {}).get("date")
    first_line = (commit.get("message") or "").split("\n", 1)[0].strip()

    normalized_commit: dict[str, Any] = {"author": {"date": author_date}}
    if committer_date:
        normalized_commit["committer"] = {"date": committer_date}
    return {
        "sha": item.get("sha"),
        "message": first_line[:200],
        "commit": normalized_commit,
    }


def sort_published_releases(
    releases: list[dict[str, Any]],
    include_prereleases: bool = False,
) -> list[dict[str, Any]]:
    """Releases publicadas (não-draft, com data), da mais antiga à mais nova."""

    return sorted(
        (
            release
            for release in releases
            if release.get("published_at")
            and release.get("draft") is not True
            and (include_prereleases or not release.get("prerelease"))
        ),
        key=lambda release: (release["published_at"], release.get("id") or 0),
    )


def collect_release_commits(
    client: GitHubClient,
    repository: dict[str, Any],
    previous_release: dict[str, Any],
    release: dict[str, Any],
) -> dict[str, Any]:
    """Commits de ``release`` em relação a ``previous_release`` (com cache).

    Retorna ``{"items": [...], "not_found": bool}``. Respostas 404/422 (tag
    apagada/reescrita, sem ancestral comum) viram ``not_found=True``: o caso
    é registrado no cache e a release é ignorada no lead time (FAQ do
    enunciado), sem derrubar a coleta do repositório.
    """

    full_name = repository["full_name"]
    owner = repository.get("owner") or full_name.split("/", 1)[0]
    name = repository.get("name") or full_name.split("/", 1)[1]
    base = previous_release["tag_name"]
    head = release["tag_name"]
    key = make_compare_key(
        previous_release["published_at"], release["published_at"], base, head
    )
    path = (
        f"/repos/{owner}/{name}/compare/"
        f"{quote(base, safe='/')}...{quote(head, safe='/')}"
    )

    cached = load_cached_repository(full_name) or {}
    state = ((cached.get("_pipeline_cache") or {}).get(CACHE_KEY) or {}).get(key) or {}
    if state.get("not_found"):
        return {"items": [], "not_found": True}  # 404 já registrado: sem nova chamada

    try:
        items = collect_cached_paginated(
            client,
            full_name,
            path,
            cache_key=CACHE_KEY,
            cache_subkey=key,
            params={"per_page": 100},
            items_key="commits",
            transform=normalize_compare_commit,
        )
    except RuntimeError as error:
        if not any(code in str(error) for code in _NOT_FOUND_CODES):
            raise
        cached = load_cached_repository(full_name) or {"full_name": full_name}
        group = cached.setdefault("_pipeline_cache", {}).setdefault(
            CACHE_KEY, {}
        )
        group[key] = {
            "items": [],
            "next_url": None,
            "complete": True,
            "not_found": True,
        }
        save_cached_repository(cached)
        return {"items": [], "not_found": True}

    return {"items": items, "not_found": False}


def releases_to_compare(
    releases_all: list[dict[str, Any]],
    observation_start: str | None,
    observation_end: str | None,
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    """Pares (release anterior, release R) para cada R publicada na janela.

    A release anterior pode estar fora da janela (enunciado, RQ 02). A
    primeira release da história do repositório não tem anterior e não gera
    par. Só releases estáveis (``draft=false`` e ``prerelease=false``).
    """

    start = parse_iso(observation_start)
    end = parse_iso(observation_end)
    ordered = sort_published_releases(releases_all)
    pairs = []
    for previous, current in zip(ordered, ordered[1:]):
        published = parse_iso(current["published_at"])
        if published is None:
            continue
        if (start and published < start) or (end and published > end):
            continue
        if not previous.get("tag_name") or not current.get("tag_name"):
            continue
        pairs.append((previous, current))
    return pairs


def collect_window_commits(
    client: GitHubClient,
    repository: dict[str, Any],
    releases_all: list[dict[str, Any]],
    observation_start: str | None,
    observation_end: str | None,
) -> dict[str, Any]:
    """Coleta o ``compare`` de todas as releases da janela.

    Retorna um resumo ``{"n_pairs", "n_not_found", "errors": [...]}``. Erros
    inesperados de uma release são registrados e a coleta segue para as
    demais (a release com erro fica sem cache completo e será retomada na
    próxima execução).
    """

    summary: dict[str, Any] = {"n_pairs": 0, "n_not_found": 0, "errors": []}
    for previous, current in releases_to_compare(
        releases_all, observation_start, observation_end
    ):
        summary["n_pairs"] += 1
        try:
            result = collect_release_commits(
                client, repository, previous, current
            )
        except Exception as error:  # noqa: BLE001 - registrar e continuar
            summary["errors"].append(
                f"{current.get('tag_name')}: {type(error).__name__}: {error}"
            )
            continue
        if result["not_found"]:
            summary["n_not_found"] += 1
    return summary
