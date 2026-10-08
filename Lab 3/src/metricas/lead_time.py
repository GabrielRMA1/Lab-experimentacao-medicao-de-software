"""Cálculo do Lead Time for Changes (RQ 02) — Parte B da S01.

Este módulo é **apenas cálculo**: ele não chama a API do GitHub. Ele lê os
dados que os coletores já salvaram (releases + commits entre releases) e
aplica a definição operacional do professor:

* Unidade de entrega ("deploy"): release publicada (``draft=false``).
* Data do commit: ``commit.author.date``.
* Data da entrega: ``published_at`` da release R.
* (a) Por release : lead time de R = data de R − data do commit MAIS ANTIGO
  incluído em R. Valor do repositório = mediana entre as releases.
* (b) Por commit  : cada commit de R tem lead time = data de R − data do
  commit. Valor do repositório = mediana de TODOS os commits de TODAS as
  releases.
* A primeira release (sem release anterior) é ignorada.

Unidade de saída: **horas**.
"""

from __future__ import annotations

import csv
import json
import os
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]  # pasta "Lab 3"
CACHE_DIR = ROOT / "data" / "cache"
RESULTS_DIR = ROOT / "data" / "results"

SECONDS_PER_HOUR = 3600.0


def parse_iso(value: str | None) -> datetime | None:
    """Converte '2025-03-15T10:00:00Z' em datetime com fuso. None se inválido."""
    if not value or not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def hours_between(start: datetime, end: datetime) -> float:
    """Diferença ``end - start`` em horas."""
    return (end - start).total_seconds() / SECONDS_PER_HOUR


def median_or_none(values: list[float]) -> float | None:
    return statistics.median(values) if values else None


def iqr_or_none(values: list[float]) -> tuple[float, float] | None:
    """(Q1, Q3). Precisa de pelo menos 2 valores."""
    if len(values) < 2:
        return None
    q1, _, q3 = statistics.quantiles(values, n=4, method="inclusive")
    return q1, q3


def compute_release_lead_time(
    release_published_at: str | None,
    commits: list[dict[str, Any]],
    seen_shas: set[str] | None = None,
) -> dict[str, Any]:
    """Lead time de UMA release.

    ``commits`` é a lista de commits entre a release anterior e esta.
    ``seen_shas`` (opcional) evita contar o mesmo commit em duas releases.

    Retorna um dict com:
      status                 'ok' | 'sem_commits' | 'release_sem_data'
      lead_time_release_h    data(R) − commit mais antigo (variante a)
      commit_lead_times_h    lista com o lead time de cada commit (variante b)
      n_commits              commits válidos usados
      n_invalidos            commits sem data ou com data posterior à release
      n_duplicados           commits repetidos (mesmo sha) ignorados
    """
    result: dict[str, Any] = {
        "status": "ok",
        "lead_time_release_h": None,
        "commit_lead_times_h": [],
        "n_commits": 0,
        "n_invalidos": 0,
        "n_duplicados": 0,
    }

    release_date = parse_iso(release_published_at)
    if release_date is None:
        result["status"] = "release_sem_data"
        return result

    if seen_shas is None:
        seen_shas = set()

    lead_times: list[float] = []
    for commit in commits:
        sha = commit.get("sha")
        if sha is not None:
            if sha in seen_shas:
                result["n_duplicados"] += 1
                continue
            seen_shas.add(sha)

        author = (commit.get("commit") or {}).get("author") or {}
        commit_date = parse_iso(author.get("date"))
        if commit_date is None or commit_date > release_date:
            result["n_invalidos"] += 1
            continue

        lead_times.append(hours_between(commit_date, release_date))

    if not lead_times:
        result["status"] = "sem_commits"
        return result

    result["commit_lead_times_h"] = lead_times
    result["n_commits"] = len(lead_times)
    result["lead_time_release_h"] = max(lead_times)
    return result



def compute_repository_lead_time(
    full_name: str,
    commits_between_releases: list[dict[str, Any]],
    observation_start: str | None = None,
    observation_end: str | None = None,
) -> dict[str, Any]:
    """Lead time (a) e (b) de um repositório.

    ``commits_between_releases`` segue o formato produzido por ``main.py``::

        [{"from_release": "v1.0", "to_release": "v1.1",
          "since": "...", "until": "<published_at de v1.1>",
          "commits": [{"sha": "...", "commit": {"author": {"date": "..."}}}]}]
    """
    start = parse_iso(observation_start)
    end = parse_iso(observation_end)

    intervals = sorted(
        commits_between_releases or [],
        key=lambda item: item.get("until") or "",
    )

    release_lead_times: list[float] = []
    all_commit_lead_times: list[float] = []
    seen_shas: set[str] = set()
    n_sem_commits = n_fora_janela = n_sem_data = 0
    n_invalidos = n_duplicados = 0

    for interval in intervals:
        until = parse_iso(interval.get("until"))
        if until is not None and (
            (start and until < start) or (end and until > end)
        ):
            n_fora_janela += 1
            continue

        outcome = compute_release_lead_time(
            interval.get("until"),
            interval.get("commits") or [],
            seen_shas,
        )
        n_invalidos += outcome["n_invalidos"]
        n_duplicados += outcome["n_duplicados"]

        if outcome["status"] == "release_sem_data":
            n_sem_data += 1
        elif outcome["status"] == "sem_commits":
            n_sem_commits += 1
        else:
            release_lead_times.append(outcome["lead_time_release_h"])
            all_commit_lead_times.extend(outcome["commit_lead_times_h"])

    iqr_release = iqr_or_none(release_lead_times)
    iqr_commit = iqr_or_none(all_commit_lead_times)

    return {
        "full_name": full_name,
        "n_releases_avaliadas": len(release_lead_times),
        "n_releases_sem_commits": n_sem_commits,
        "n_releases_sem_data": n_sem_data,
        "n_releases_fora_janela": n_fora_janela,
        "n_commits": len(all_commit_lead_times),
        "n_commits_invalidos": n_invalidos,
        "n_commits_duplicados": n_duplicados,
        "lead_time_release_mediana_h": median_or_none(release_lead_times),
        "lead_time_release_q1_h": iqr_release[0] if iqr_release else None,
        "lead_time_release_q3_h": iqr_release[1] if iqr_release else None,
        "lead_time_commit_mediana_h": median_or_none(all_commit_lead_times),
        "lead_time_commit_q1_h": iqr_commit[0] if iqr_commit else None,
        "lead_time_commit_q3_h": iqr_commit[1] if iqr_commit else None,
    }



def intervals_from_cache(cache_record: dict[str, Any]) -> list[dict[str, Any]]:
    """Converte ``_pipeline_cache`` no formato de ``commits_between_releases``.

    Chave do cache: ``"<since>|<until>"``; ``until`` = published_at da release.
    """
    cached = (cache_record.get("_pipeline_cache") or {}).get(
        "commits_between_releases"
    ) or {}
    intervals = []
    for key, value in cached.items():
        since, _, until = key.partition("|")
        intervals.append(
            {
                "since": since,
                "until": until,
                "commits": value.get("items") or [],
                "complete": value.get("complete", True),
            }
        )
    return intervals


def compute_from_cache_dir(
    cache_dir: Path = CACHE_DIR,
    observation_start: str | None = None,
    observation_end: str | None = None,
) -> list[dict[str, Any]]:
    """Calcula o lead time de todos os repositórios do cache."""
    rows = []
    for path in sorted(Path(cache_dir).glob("*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        full_name = record.get("full_name") or path.stem.replace("__", "/", 1)
        intervals = intervals_from_cache(record)
        row = compute_repository_lead_time(
            full_name, intervals, observation_start, observation_end
        )
        row["coleta_incompleta"] = any(
            not item["complete"] for item in intervals
        )
        rows.append(row)
    return rows



def save_results(rows: list[dict[str, Any]], output_dir: Path = RESULTS_DIR) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "lead_time.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if rows:
        with (output_dir / "lead_time.csv").open(
            "w", newline="", encoding="utf-8"
        ) as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)


def main() -> None:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    start = os.getenv("OBSERVATION_START")
    end = os.getenv("OBSERVATION_END")
    rows = compute_from_cache_dir(
        observation_start=start, observation_end=end
    )
    save_results(rows)
    com_dado = [r for r in rows if r["lead_time_release_mediana_h"] is not None]
    print(f"Repositórios no cache: {len(rows)}")
    print(f"Com lead time calculado: {len(com_dado)}")
    print(f"Resultados em: {RESULTS_DIR}")


if __name__ == "__main__":
    main()
