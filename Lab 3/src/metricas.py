"""Cálculo das métricas DORA da Parte C (CFR e tempo de recuperação).

As funções deste módulo trabalham somente com os dados já coletados pelo
pipeline. Nenhuma chamada à API do GitHub é feita aqui.
"""

from __future__ import annotations

from datetime import datetime
from statistics import median
from typing import Any


_FAILURES = {"failure", "timed_out", "startup_failure"}
_SUCCESS = {"success"}


def _parse_datetime(value: str) -> datetime:
    if not value:
        raise ValueError("Data obrigatória não informada.")
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def calculate_cfr_ci(workflow_runs: list[dict[str, Any]]) -> dict[str, Any]:
    """Calcula o CFR (a), usando workflow runs como proxy de falha de CI.

    A definição segue o enunciado: runs ``success`` e ``failure`` entram no
    denominador; ``cancelled``, ``skipped``, ``neutral``, ``action_required``,
    ``stale`` e runs sem conclusão são ignorados.
    """

    successes = sum(
        1
        for run in workflow_runs
        if run.get("classification") == "success"
        or run.get("conclusion") in _SUCCESS
    )
    failures = sum(
        1
        for run in workflow_runs
        if run.get("classification") == "failure"
        or run.get("conclusion") in _FAILURES
    )
    evaluated = successes + failures

    return {
        "successes": successes,
        "failures": failures,
        "evaluated_runs": evaluated,
        "cfr": failures / evaluated if evaluated else None,
    }


def calculate_recovery_time(
    workflow_runs: list[dict[str, Any]],
) -> dict[str, Any]:
    """Calcula o tempo de recuperação por episódio, em horas.

    Runs são agrupadas por workflow e ordenadas cronologicamente. Um episódio
    começa na primeira falha após um sucesso e termina no próximo sucesso do
    mesmo workflow. Episódios sem sucesso posterior são censurados.
    """

    grouped: dict[Any, list[dict[str, Any]]] = {}
    for run in workflow_runs:
        classification = run.get("classification")
        if classification not in {"success", "failure"}:
            if run.get("conclusion") not in (_SUCCESS | _FAILURES):
                continue
            classification = (
                "success" if run.get("conclusion") in _SUCCESS else "failure"
            )

        workflow = run.get("workflow_id")
        if workflow is None:
            workflow = run.get("workflow_name", run.get("name"))
        if workflow is None:
            raise ValueError(
                "Recovery Time exige 'workflow_id' ou 'workflow_name' "
                "para agrupar runs do mesmo workflow."
            )

        grouped.setdefault(workflow, []).append(
            {**run, "classification": classification}
        )

    episodes: list[dict[str, Any]] = []

    for workflow, runs in grouped.items():
        runs.sort(
            key=lambda run: (
                _parse_datetime(run["run_started_at"]),
                run.get("id", 0),
            )
        )

        active_failure: dict[str, Any] | None = None
        has_success = False
        for run in runs:
            classification = run["classification"]

            if classification == "success":
                has_success = True
                if active_failure is not None:
                    start = _parse_datetime(active_failure["run_started_at"])
                    end = _parse_datetime(run["updated_at"])
                    hours = (end - start).total_seconds() / 3600
                    episodes.append(
                        {
                            "workflow": workflow,
                            "failure_run_id": active_failure.get("id"),
                            "recovery_run_id": run.get("id"),
                            "recovered": True,
                            "censored": False,
                            "recovery_hours": hours,
                        }
                    )
                    active_failure = None
                continue

            if has_success and active_failure is None:
                active_failure = run

        if active_failure is not None:
            episodes.append(
                {
                    "workflow": workflow,
                    "failure_run_id": active_failure.get("id"),
                    "recovery_run_id": None,
                    "recovered": False,
                    "censored": True,
                    "recovery_hours": None,
                }
            )

    recovered = [
        episode["recovery_hours"]
        for episode in episodes
        if episode["recovered"]
    ]
    censored = sum(1 for episode in episodes if episode["censored"])

    return {
        "episodes": episodes,
        "recovered_episodes": len(recovered),
        "censored_episodes": censored,
        "total_episodes": len(episodes),
        "censored_rate": censored / len(episodes) if episodes else None,
        "recovery_times_hours": recovered,
        "median_hours": median(recovered) if recovered else None,
    }
