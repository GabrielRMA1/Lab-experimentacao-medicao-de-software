"""Sorteio da amostra-ouro e geração do material de rotulagem (seção 6).

* Sorteia ``N_REPOS`` (60) repositórios do dataset final com ``random_state=42``
  (reprodutível) e, para cada um, ``N_RELEASES_POR_REPO`` (5) releases da
  janela — também com semente fixa por repositório.
* Gera o **pacote de rotulagem** (``pacote_rotulagem.json``): para cada
  release, as notas e as mensagens dos commits — o que o rotulador precisa
  ler. **Não inclui nada da heurística** (rotulagem às cegas).
* Gera modelos de planilha (``*_TEMPLATE.csv``) com link direto para a release.
"""

from __future__ import annotations

import csv
import json
import random
from pathlib import Path
from typing import Any

import pandas as pd

from src.metricas.cfr_release import commits_by_tag_from_cache
from src.metricas.lead_time import parse_iso
from src.validacao import (
    N_RELEASES_POR_REPO,
    N_REPOS,
    SEED,
    VALIDACAO_DIR,
)

MAX_NOTES_CHARS = 1500
MAX_COMMITS_SHOWN = 30


def sample_repositories(
    full_names: list[str], n: int = N_REPOS, seed: int = SEED
) -> list[str]:
    """Sorteio reprodutível: ``df.sample(n=n, random_state=seed)``."""

    frame = pd.DataFrame({"full_name": sorted(full_names)})
    if len(frame) < n:
        raise ValueError(
            f"A amostra final tem {len(frame)} repositórios; "
            f"são necessários pelo menos {n} para a amostra-ouro."
        )
    return frame.sample(n=n, random_state=seed)["full_name"].tolist()


def eligible_releases(
    cache_record: dict[str, Any],
    observation_start: str | None,
    observation_end: str | None,
) -> list[dict[str, Any]]:
    """Releases estáveis da janela com lista de commits disponível."""

    start, end = parse_iso(observation_start), parse_iso(observation_end)
    pipeline = cache_record.get("_pipeline_cache") or {}
    releases = (pipeline.get("releases_v2") or {}).get("items") or []
    with_commits = commits_by_tag_from_cache(cache_record)
    eligible = []
    for release in releases:
        published = parse_iso(release.get("published_at"))
        if (
            published is None
            or release.get("prerelease")
            or release.get("draft")
            or release.get("tag_name") not in with_commits
            or not with_commits[release["tag_name"]]
        ):
            continue
        if (start and published < start) or (end and published > end):
            continue
        eligible.append(release)
    eligible.sort(key=lambda r: (r["published_at"], r.get("id") or 0))
    return eligible


def pick_releases(
    full_name: str,
    eligible: list[dict[str, Any]],
    k: int = N_RELEASES_POR_REPO,
    seed: int = SEED,
) -> list[dict[str, Any]]:
    """Sorteia ``k`` releases (semente fixa por repositório), em ordem cronológica."""

    rng = random.Random(f"{seed}:{full_name}")
    chosen = rng.sample(eligible, min(k, len(eligible)))
    return sorted(chosen, key=lambda r: (r["published_at"], r.get("id") or 0))


def build_package(
    selected: list[str],
    load_record,
    observation_start: str | None,
    observation_end: str | None,
) -> list[dict[str, Any]]:
    """Monta o pacote de rotulagem. ``load_record(full_name)`` lê o cache."""

    package = []
    for full_name in selected:
        record = load_record(full_name) or {}
        commits = commits_by_tag_from_cache(record)
        eligible = eligible_releases(record, observation_start, observation_end)
        releases = []
        for release in pick_releases(full_name, eligible):
            messages = [c.get("message", "") for c in commits[release["tag_name"]]]
            releases.append(
                {
                    "tag_name": release["tag_name"],
                    "url": release.get("html_url"),
                    "name": release.get("name"),
                    "published_at": release.get("published_at"),
                    "notes": (release.get("body") or "")[:MAX_NOTES_CHARS],
                    "n_commits": len(messages),
                    "commit_messages": messages[:MAX_COMMITS_SHOWN],
                }
            )
        package.append(
            {
                "full_name": full_name,
                "url": record.get("html_url") or f"https://github.com/{full_name}",
                "language": record.get("language"),
                "stars": record.get("stars"),
                "releases": releases,
            }
        )
    return package


def write_outputs(
    package: list[dict[str, Any]], output_dir: Path = VALIDACAO_DIR
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "amostra": output_dir / "amostra_ouro.csv",
        "pacote": output_dir / "pacote_rotulagem.json",
        "repos": output_dir / "rotulos_repos_TEMPLATE.csv",
        "releases": output_dir / "rotulos_releases_TEMPLATE.csv",
    }
    paths["pacote"].write_text(
        json.dumps(package, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    with paths["amostra"].open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["full_name", "url", "n_releases_sorteadas"])
        for repo in package:
            writer.writerow([repo["full_name"], repo["url"], len(repo["releases"])])
    with paths["repos"].open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["full_name", "url", "tipo_projeto", "entregas_reais"])
        for repo in package:
            writer.writerow([repo["full_name"], repo["url"], "", ""])
    with paths["releases"].open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["full_name", "tag_name", "release_url", "corretiva"])
        for repo in package:
            for release in repo["releases"]:
                writer.writerow(
                    [repo["full_name"], release["tag_name"], release["url"], ""]
                )
    return paths
