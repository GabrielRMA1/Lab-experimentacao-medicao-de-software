"""Consolidação do dataset final (uma linha por repositório da amostra)."""

from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from src.collectors.commits_compare import sort_published_releases
from src.metricas import calculate_cfr_ci, calculate_recovery_time
from src.metricas.cfr_release import commits_by_tag_from_cache, compute_cfr_release
from src.metricas.heuristica import DEFAULT_VERSION, VERSIONS, classify_releases
from src.metricas.lead_time import (
    compute_repository_lead_time,
    intervals_from_cache,
    parse_iso,
)
from src.pipeline.config import Config
from src.pipeline.dicionario import COLUMN_NAMES, write_dictionary


def chosen_heuristic_version(cfg: Config) -> str:
    """Versão da heurística: ``HEURISTICA_VERSAO`` > escolhida na validação > padrão."""

    if cfg.heuristica_versao:
        version = cfg.heuristica_versao
    else:
        path = cfg.validacao_dir / "heuristica_escolhida.json"
        version = DEFAULT_VERSION
        if path.exists():
            version = json.loads(path.read_text(encoding="utf-8")).get("versao", version)
    if version not in VERSIONS:
        raise KeyError(f"Versão de heurística desconhecida: {version}")
    return version


def releases_from_record(record: dict[str, Any]) -> list[dict[str, Any]]:
    cache = (record.get("_pipeline_cache") or {}).get("releases_v2") or {}
    return cache.get("items") or []


def workflow_runs_from_record(
    record: dict[str, Any], start: str, end: str
) -> list[dict[str, Any]]:
    """Runs da janela, a partir do cache mensal (deduplicadas por ``id``)."""

    groups = (record.get("_pipeline_cache") or {}).get("workflow_runs_monthly_v1") or {}
    lo, hi = parse_iso(start), parse_iso(end)
    seen: set[Any] = set()
    runs = []
    for state in groups.values():
        for run in state.get("items") or []:
            created = parse_iso(run.get("created_at"))
            if created is None or not (lo <= created <= hi) or run.get("id") in seen:
                continue
            seen.add(run.get("id"))
            runs.append(run)
    return runs


def window_weeks(start: str, end: str) -> float:
    return (parse_iso(end) - parse_iso(start)).total_seconds() / 86400 / 7


def build_row(
    record: dict[str, Any], cfg: Config, version: str
) -> dict[str, Any]:
    start, end = cfg.observation_start, cfg.observation_end
    lo, hi = parse_iso(start), parse_iso(end)
    full_name = record["full_name"]

    releases = releases_from_record(record)
    stable = sort_published_releases(releases)
    in_window = [r for r in stable if lo <= parse_iso(r["published_at"]) <= hi]
    prereleases = [
        r for r in sort_published_releases(releases, include_prereleases=True)
        if r.get("prerelease") and lo <= parse_iso(r["published_at"]) <= hi
    ]

    intervals = intervals_from_cache(record)
    lead = compute_repository_lead_time(full_name, intervals, start, end)

    runs = workflow_runs_from_record(record, start, end)
    ci = calculate_cfr_ci(runs)
    recovery = calculate_recovery_time(runs)

    classified = classify_releases(stable, commits_by_tag_from_cache(record), version)
    cfr_b = compute_cfr_release(classified, start, end)

    created_at = record.get("created_at")
    age_days = (
        (hi - parse_iso(created_at)).days if parse_iso(created_at) else None
    )
    row = {
        "full_name": full_name,
        "html_url": record.get("html_url"),
        "language": record.get("language"),
        "stars": record.get("stars"),
        "forks": record.get("forks"),
        "contributors": record.get("contributors"),
        "created_at": created_at,
        "idade_dias_fim_janela": age_days,
        "default_branch": record.get("default_branch"),
        "n_releases": len(in_window),
        "n_prereleases_janela": len(prereleases),
        "deploy_freq_semana": len(in_window) / window_weeks(start, end),
        "lt_release_mediana_h": lead["lead_time_release_mediana_h"],
        "lt_release_q1_h": lead["lead_time_release_q1_h"],
        "lt_release_q3_h": lead["lead_time_release_q3_h"],
        "lt_commit_mediana_h": lead["lead_time_commit_mediana_h"],
        "lt_commit_q1_h": lead["lead_time_commit_q1_h"],
        "lt_commit_q3_h": lead["lead_time_commit_q3_h"],
        "lt_n_releases_avaliadas": lead["n_releases_avaliadas"],
        "lt_n_commits": lead["n_commits"],
        "lt_n_releases_compare_404": lead["n_releases_compare_404"],
        "ci_n_sucessos": ci["successes"],
        "ci_n_falhas": ci["failures"],
        "cfr_ci": ci["cfr"],
        "heuristica_versao": version,
        "cfr_n_avaliadas": cfr_b["n_releases_avaliadas"],
        "cfr_n_falhas": cfr_b["n_releases_falha"],
        "cfr_n_censuradas": cfr_b["n_releases_censuradas"],
        "cfr_entrega": cfr_b["cfr_entrega"],
        "n_releases_corretivas": cfr_b["n_releases_corretivas"],
        "rework_rate": cfr_b["rework_rate"],
        "rec_n_episodios": recovery["total_episodes"],
        "rec_n_censurados": recovery["censored_episodes"],
        "rec_prop_censurados": recovery["censored_rate"],
        "rec_mediana_h": recovery["median_hours"],
        "rec_q1_h": recovery["q1_hours"],
        "rec_q3_h": recovery["q3_hours"],
        "coleta_incompleta": any(not i["complete"] for i in intervals),
        "runs_intervalos_truncados": len(
            (record.get("_pipeline_cache") or {}).get("runs_truncados_v1") or []
        ),
    }
    assert list(row) == COLUMN_NAMES, "colunas do CSV divergem do dicionário"
    return row


def build_dataset(
    names: list[str],
    load_record: Callable[[str], dict[str, Any] | None],
    cfg: Config,
    version: str | None = None,
) -> list[dict[str, Any]]:
    version = version or chosen_heuristic_version(cfg)
    rows = []
    for name in names:
        record = load_record(name)
        if record is None:
            raise FileNotFoundError(f"Sem cache para {name}; rode `collect`.")
        rows.append(build_row(record, cfg, version))
    return rows


def write_dataset(rows: list[dict[str, Any]], dataset_dir: Path) -> Path:
    dataset_dir.mkdir(parents=True, exist_ok=True)
    path = dataset_dir / "dataset_repos.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMN_NAMES)
        writer.writeheader()
        writer.writerows(rows)
    return path


def write_dictionary_files(dataset_dir: Path, docs_dir: Path) -> None:
    write_dictionary(dataset_dir / "dicionario_dados.csv", docs_dir / "DICIONARIO_DADOS.md")
