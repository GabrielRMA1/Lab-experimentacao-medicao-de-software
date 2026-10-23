"""Seleção e coleta por repositório, com descarte antecipado (S02).

Ordem das etapas (da mais barata para a mais cara), cada uma com cache e
retomada — se a coleta cair, rodar de novo continua de onde parou:

1. metadados (+ contribuidores)           -> 1–2 chamadas
2. ``total_count`` de workflows            -> 1 chamada   (0 = sem Actions)
3. releases (histórico completo)           -> 1–3 chamadas (>= 5 estáveis na janela)
4. workflow runs, janela dividida por mês  -> ~12+ chamadas (>= 50 runs válidos)
5. ``compare`` de cada release da janela   -> 1 chamada por release

O resultado de cada repositório (aceito/descartado + motivo) é gravado no
próprio cache em ``_pipeline_cache["decision"]``; o funil é reconstruído a
partir dessas decisões, inclusive de coletas feitas em outras máquinas
(basta juntar as pastas ``data/cache``).
"""

from __future__ import annotations

import json
import math
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from src.collectors.commits_compare import (
    collect_window_commits,
    sort_published_releases,
)
from src.collectors.repositories import (
    GitHubClient,
    collect_repository_metadata,
    collect_repository_releases_full,
    collect_repository_workflow_runs,
    get_contributor_count,  # noqa: F401  (reexport p/ testes)
    get_pipeline_value,
    get_workflow_count,
    set_pipeline_value,
)
from src.metricas.lead_time import parse_iso
from src.pipeline.config import Config

# Motivos de descarte (usados no funil)
SEM_ACTIONS = "sem_actions"
POUCAS_RELEASES = "menos_de_5_releases"
POUCOS_RUNS = "menos_de_50_runs_validos"

SEARCH_FIELDS = (
    "full_name", "name", "html_url", "default_branch", "language",
    "stargazers_count", "forks_count", "created_at", "updated_at",
    "archived", "fork",
)


# ---------------------------------------------------------------- candidatos

def to_candidate(item: dict[str, Any]) -> dict[str, Any]:
    """Reduz um item da Search API ao mínimo necessário (e estável)."""

    candidate = {key: item.get(key) for key in SEARCH_FIELDS}
    candidate["owner"] = {"login": (item.get("owner") or {}).get("login")}
    return candidate


def save_candidates(path: Path, items: list[dict[str, Any]], query: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "query": query,
        "searched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "count": len(items),
        "items": [to_candidate(item) for item in items],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")


def load_candidates(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(
            f"{path} não existe. Rode primeiro: python -m src.pipeline search "
            "(ou copie o candidates.json compartilhado do repositório)."
        )
    return json.loads(path.read_text(encoding="utf-8"))["items"]


# ------------------------------------------------------------------ decisão

def count_valid_runs(
    runs: list[dict[str, Any]], start: str, end: str
) -> list[dict[str, Any]]:
    """Runs que entram nos cálculos: sucesso/falha criados dentro da janela."""

    lo, hi = parse_iso(start), parse_iso(end)
    valid = []
    for run in runs:
        created = parse_iso(run.get("created_at"))
        if created is None or not (lo <= created <= hi):
            continue
        if run.get("classification") in ("success", "failure"):
            valid.append(run)
    return valid


def stable_releases_in_window(
    releases: list[dict[str, Any]], start: str, end: str
) -> list[dict[str, Any]]:
    lo, hi = parse_iso(start), parse_iso(end)
    return [
        r for r in sort_published_releases(releases)
        if lo <= parse_iso(r["published_at"]) <= hi
    ]


def _decision(status: str, cfg: Config, stage: str, reason: str | None = None,
              **counts: Any) -> dict[str, Any]:
    return {
        "status": status,
        "stage": stage,
        "reason": reason,
        "counts": counts,
        "config": cfg.window_signature(),
        "decided_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def evaluate_candidate(
    client: GitHubClient, candidate: dict[str, Any], cfg: Config
) -> dict[str, Any]:
    """Coleta (com descarte antecipado) e devolve a decisão do repositório.

    Decisões ``accepted``/``discarded`` são gravadas no cache. Se alguma etapa
    terminar com erro, devolve ``status="error"`` SEM gravar — a próxima
    execução tenta de novo, aproveitando as páginas já em cache.
    """

    full_name = candidate["full_name"]
    cached = get_pipeline_value(full_name, "decision")
    if cached and cached.get("config") == cfg.window_signature():
        return cached

    metadata = collect_repository_metadata(client, candidate)
    owner, name = metadata["owner"], metadata["name"]

    n_workflows = get_pipeline_value(full_name, "workflows_count")
    if n_workflows is None:
        n_workflows = get_workflow_count(client, owner, name)
        set_pipeline_value(full_name, "workflows_count", n_workflows)
    if n_workflows == 0:
        return _store(full_name, _decision("discarded", cfg, "actions", SEM_ACTIONS))

    releases = collect_repository_releases_full(client, metadata)
    in_window = stable_releases_in_window(
        releases, cfg.observation_start, cfg.observation_end
    )
    if len(in_window) < cfg.min_releases:
        return _store(full_name, _decision(
            "discarded", cfg, "releases", POUCAS_RELEASES,
            n_releases=len(in_window)))

    print(f"  ... {full_name}: {len(in_window)} releases na janela; coletando workflow runs")
    runs = collect_repository_workflow_runs(
        client, metadata,
        observation_start=cfg.observation_start,
        observation_end=cfg.observation_end,
    )
    valid_runs = count_valid_runs(runs, cfg.observation_start, cfg.observation_end)
    if len(valid_runs) < cfg.min_runs:
        return _store(full_name, _decision(
            "discarded", cfg, "runs", POUCOS_RUNS,
            n_releases=len(in_window), n_runs=len(valid_runs)))

    print(f"  ... {full_name}: {len(valid_runs)} runs válidos; coletando commits de cada release")
    summary = collect_window_commits(
        client, metadata, releases, cfg.observation_start, cfg.observation_end
    )
    if summary["errors"]:
        return _decision(
            "error", cfg, "compare",
            "; ".join(summary["errors"][:3]),
            n_errors=len(summary["errors"]),
        )
    return _store(full_name, _decision(
        "accepted", cfg, "final",
        n_releases=len(in_window), n_runs=len(valid_runs),
        n_compare=summary["n_pairs"], n_compare_404=summary["n_not_found"]))


def _store(full_name: str, decision: dict[str, Any]) -> dict[str, Any]:
    set_pipeline_value(full_name, "decision", decision)
    return decision


# ------------------------------------------------------------------- coleta

def parse_shard(text: str | None) -> tuple[int, int]:
    """``"2/3"`` -> ``(1, 3)`` (índice 0-based, total). ``None`` -> ``(0, 1)``."""

    if not text:
        return 0, 1
    index, _, total = text.partition("/")
    index, total = int(index), int(total)
    if total < 1 or not 1 <= index <= total:
        raise ValueError("Use --shard I/N com 1 <= I <= N (ex.: --shard 2/3).")
    return index - 1, total


def assigned_candidates(
    candidates: list[dict[str, Any]], shard: tuple[int, int]
) -> list[dict[str, Any]]:
    """Candidatos (ordenados por estrelas) cabendo a este fatiamento."""

    ordered = sorted(candidates, key=lambda c: c.get("stargazers_count") or 0, reverse=True)
    index, total = shard
    return [c for i, c in enumerate(ordered) if i % total == index]


def collect(
    client: GitHubClient,
    candidates: list[dict[str, Any]],
    cfg: Config,
    shard: tuple[int, int] = (0, 1),
    evaluate: Callable[..., dict[str, Any]] = evaluate_candidate,
    log: Callable[[str], None] = print,
) -> dict[str, int]:
    """Avalia os candidatos do fatiamento até atingir a cota de aceitos.

    A cota do fatiamento é ``ceil(sample_target / total)``; o que já está em
    cache conta (e custa zero chamadas). Há sempre ``workers`` repositórios
    em avaliação: quando um termina, o próximo começa — um repositório
    gigante não segura os demais. Pode ser interrompida com Ctrl+C e
    retomada rodando o mesmo comando.
    """

    mine = assigned_candidates(candidates, shard)
    goal = math.ceil(cfg.sample_target / shard[1])
    stats = {"accepted": 0, "discarded": 0, "error": 0, "evaluated": 0}
    workers = max(cfg.workers, 1)
    queue = iter(mine)
    running: dict[Future, dict[str, Any]] = {}

    def submit_next() -> None:
        candidate = next(queue, None)
        if candidate is not None:
            running[executor.submit(evaluate, client, candidate, cfg)] = candidate

    executor = ThreadPoolExecutor(max_workers=workers)
    try:
        for _ in range(workers):
            submit_next()
        while running:
            done, _ = wait(list(running), return_when=FIRST_COMPLETED)
            for future in done:
                candidate = running.pop(future)
                try:
                    decision = future.result()
                except Exception as error:  # noqa: BLE001
                    stats["error"] += 1
                    log(f"[ERRO] {candidate['full_name']}: {type(error).__name__}: {error}")
                else:
                    stats["evaluated"] += 1
                    stats[decision["status"]] = stats.get(decision["status"], 0) + 1
                    if decision["status"] == "error":
                        log(f"[ERRO] {candidate['full_name']}: {decision['reason']}")
                    else:
                        log(
                            f"[{stats['accepted']}/{goal} aceitos] "
                            f"{candidate['full_name']}: {decision['status']}"
                            + (f" ({decision['reason']})" if decision["reason"] else "")
                        )
                if stats["accepted"] < goal:
                    submit_next()
            if stats["accepted"] >= goal and running:
                log(f"Cota do fatiamento atingida ({goal} aceitos); "
                    f"terminando os {len(running)} em andamento...")
                # Os que já começaram terminam (o trabalho fica em cache);
                # nenhum novo é iniciado.
        if stats["accepted"] >= goal:
            log(f"Cota do fatiamento atingida ({goal} aceitos).")
    finally:
        executor.shutdown(wait=False, cancel_futures=True)
    return stats


def read_decisions(
    candidates: list[dict[str, Any]],
    load_record: Callable[[str], dict[str, Any] | None],
) -> dict[str, dict[str, Any]]:
    """``{full_name: decisão}`` dos candidatos já avaliados (lendo o cache)."""

    decisions = {}
    for candidate in candidates:
        record = load_record(candidate["full_name"])
        decision = ((record or {}).get("_pipeline_cache") or {}).get("decision")
        if decision:
            decisions[candidate["full_name"]] = decision
    return decisions
