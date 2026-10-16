"""Avalia as versões da heurística de release corretiva contra o consenso.

Para cada versão em ``heuristica.VERSIONS`` calcula precisão, recall e F1
(``sklearn.metrics.precision_recall_fscore_support``) sobre as releases da
amostra-ouro com rótulo de consenso. A classe positiva é "corretiva".

Saídas em ``data/validacao/``:
* ``heuristica_versoes.csv``    — uma linha por versão (documente no artigo);
* ``heuristica_escolhida.json`` — versão com maior F1 (usada pelo dataset).

Se o melhor F1 ficar abaixo de 0,70, o enunciado manda refinar a heurística e
reavaliar: acrescente uma versão em ``src/metricas/heuristica.py`` e rode de novo.
Atenção: escolher a melhor versão no mesmo conjunto em que ela foi avaliada é
otimista — registre isso nas ameaças à validade.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Callable

from sklearn.metrics import precision_recall_fscore_support

from src.metricas.cfr_release import commits_by_tag_from_cache
from src.metricas.heuristica import VERSIONS, classify_releases
from src.validacao import VALIDACAO_DIR

F1_META = 0.70


def score_predictions(y_true: list[int], y_pred: list[int]) -> dict[str, Any]:
    """Precisão/recall/F1 da classe positiva + matriz de confusão."""

    precision, recall, f1, _ = precision_recall_fscore_support(
        y_true, y_pred, average="binary", pos_label=1, zero_division=0
    )
    pairs = list(zip(y_true, y_pred))
    return {
        "precisao": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "n": len(pairs),
        "vp": sum(t == 1 and p == 1 for t, p in pairs),
        "fp": sum(t == 0 and p == 1 for t, p in pairs),
        "fn": sum(t == 1 and p == 0 for t, p in pairs),
        "vn": sum(t == 0 and p == 0 for t, p in pairs),
    }


def read_consensus_releases(
    directory: Path = VALIDACAO_DIR,
) -> list[dict[str, str]]:
    with (directory / "consenso_releases.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        return list(csv.DictReader(handle))


def evaluate_versions(
    consensus: list[dict[str, str]],
    load_record: Callable[[str], dict[str, Any] | None],
    versions: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Uma linha por versão. Releases sem rótulo final de consenso são puladas."""

    versions = versions or VERSIONS
    by_repo: dict[str, list[dict[str, str]]] = {}
    for row in consensus:
        if row.get("corretiva") in ("sim", "nao"):
            by_repo.setdefault(row["full_name"], []).append(row)

    y_true: list[int] = []
    predictions: dict[str, list[int]] = {name: [] for name in versions}
    for full_name, rows in sorted(by_repo.items()):
        record = load_record(full_name) or {}
        releases = (
            (record.get("_pipeline_cache") or {}).get("releases_v2") or {}
        ).get("items") or []
        stable = sorted(
            (r for r in releases if r.get("published_at") and not r.get("prerelease")),
            key=lambda r: (r["published_at"], r.get("id") or 0),
        )
        commits = commits_by_tag_from_cache(record)
        for name in versions:
            flagged = {
                c["tag_name"]: c["is_corrective"]
                for c in classify_releases(stable, commits, name)
            }
            predictions[name].extend(
                int(flagged.get(row["tag_name"], False)) for row in rows
            )
        y_true.extend(int(row["corretiva"] == "sim") for row in rows)

    results = []
    for name in versions:
        results.append({"versao": name, **score_predictions(y_true, predictions[name])})
    return results


def write_results(
    results: list[dict[str, Any]], directory: Path = VALIDACAO_DIR
) -> dict[str, Any]:
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / "heuristica_versoes.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)
    best = max(results, key=lambda r: (r["f1"], r["precisao"]))
    chosen = {
        "versao": best["versao"],
        "f1": best["f1"],
        "precisao": best["precisao"],
        "recall": best["recall"],
        "atinge_meta_f1_0_70": best["f1"] >= F1_META,
    }
    (directory / "heuristica_escolhida.json").write_text(
        json.dumps(chosen, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return chosen


def main(directory: Path = VALIDACAO_DIR) -> None:
    from src.collectors.repositories import load_cached_repository

    consensus = read_consensus_releases(directory)
    results = evaluate_versions(consensus, load_cached_repository)
    chosen = write_results(results, directory)
    print(f"{'versão':<24}{'precisão':>10}{'recall':>9}{'F1':>7}{'n':>6}")
    for r in results:
        print(f"{r['versao']:<24}{r['precisao']:>10.3f}{r['recall']:>9.3f}{r['f1']:>7.3f}{r['n']:>6}")
    print(f"\nMelhor: {chosen['versao']} (F1 = {chosen['f1']:.3f})")
    if not chosen["atinge_meta_f1_0_70"]:
        print("F1 < 0,70: refine a heurística (nova versão em heuristica.py) e reavalie.")
