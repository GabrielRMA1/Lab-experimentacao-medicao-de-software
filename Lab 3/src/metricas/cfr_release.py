"""CFR (b) — proxy de entrega — e *rework rate* (RQ 03b e RQ 08).

Definição (enunciado, RQ 03b): uma release R é **falha** se for seguida, em
até 7 dias, por uma **release corretiva**. O CFR do repositório é
``releases que falharam ÷ releases avaliadas``. Releases publicadas nos
últimos 7 dias da janela não podem ser avaliadas (ainda não se sabe se haverá
correção): ficam fora do denominador e são contadas como **censuradas**.

*Rework rate* (bônus RQ 08): releases corretivas ÷ releases da janela.

Módulo de cálculo puro (sem API).
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from src.metricas.lead_time import parse_iso

HORIZON_DAYS = 7


def commits_by_tag_from_cache(
    cache_record: dict[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    """``{tag_da_release: commits}`` a partir do cache ``compare_v1``."""

    from src.metricas.lead_time import intervals_from_cache

    result: dict[str, list[dict[str, Any]]] = {}
    for interval in intervals_from_cache(cache_record):
        tag = interval.get("to_release")
        if tag and not interval.get("not_found"):
            result[tag] = interval["commits"]
    return result


def compute_cfr_release(
    classified_releases: list[dict[str, Any]],
    observation_start: str | None,
    observation_end: str | None,
    horizon_days: int = HORIZON_DAYS,
) -> dict[str, Any]:
    """CFR (b) e rework rate de um repositório.

    ``classified_releases``: saída de ``heuristica.classify_releases`` (ordem
    cronológica, histórico completo). Só as releases da janela entram no
    cálculo, mas as corretivas "seguintes" podem ser quaisquer posteriores a R
    até ``R + horizon_days`` (o corte de censura garante que isso cabe na janela).
    """

    start = parse_iso(observation_start)
    end = parse_iso(observation_end)
    horizon = timedelta(days=horizon_days)

    dated = []
    for item in classified_releases:
        published = parse_iso(item.get("published_at"))
        if published is not None:
            dated.append((published, bool(item.get("is_corrective"))))
    dated.sort(key=lambda pair: pair[0])

    in_window = [
        (when, corrective)
        for when, corrective in dated
        if (start is None or when >= start) and (end is None or when <= end)
    ]

    evaluated = failed = censored = 0
    for when, _ in in_window:
        if end is not None and when + horizon > end:
            censored += 1
            continue
        evaluated += 1
        if any(
            corrective and when < later <= when + horizon
            for later, corrective in dated
        ):
            failed += 1

    n_corrective = sum(1 for _, corrective in in_window if corrective)
    return {
        "n_releases_janela": len(in_window),
        "n_releases_avaliadas": evaluated,
        "n_releases_falha": failed,
        "n_releases_censuradas": censored,
        "cfr_entrega": failed / evaluated if evaluated else None,
        "n_releases_corretivas": n_corrective,
        "rework_rate": n_corrective / len(in_window) if in_window else None,
    }
