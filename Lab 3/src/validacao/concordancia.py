"""Concordância entre avaliadores (kappa de Fleiss) e consenso (seção 6).

Entradas (uma por integrante, commitadas por cada um):
``data/validacao/rotulos_<nome>_repos.csv`` e ``rotulos_<nome>_releases.csv``.

Saídas em ``data/validacao/``:
* ``concordancia.json``       — kappa de Fleiss por dimensão (+ interpretação);
* ``consenso_repos.csv``      — rótulo de consenso por repositório;
* ``consenso_releases.csv``   — rótulo de consenso por release;
* ``desempate.csv``           — casos 1-1-1 (ou sem maioria) para decidir em
  reunião. Preencha ``rotulo_final``/``justificativa`` e rode de novo.

Protocolo de desempate (documentado em ``docs/PROTOCOLO_VALIDACAO.md``):
maioria simples (>= 2 de 3); sem maioria -> reunião, registrada em
``desempate.csv``.
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

from src.validacao import DIMENSOES, VALIDACAO_DIR

KEY_COLUMNS = {"repos": ("full_name",), "releases": ("full_name", "tag_name")}


def interpret_kappa(kappa: float | None) -> str | None:
    """Faixas de Landis & Koch (1977)."""

    if kappa is None:
        return None
    if kappa < 0:
        return "pobre"
    if kappa <= 0.20:
        return "leve"
    if kappa <= 0.40:
        return "razoável"
    if kappa <= 0.60:
        return "moderada"
    if kappa <= 0.80:
        return "substancial"
    return "quase perfeita"


def fleiss_kappa_from_ratings(ratings: list[list[str]]) -> float | None:
    """Kappa de Fleiss. ``ratings[i]`` = rótulos dos avaliadores para o item i.

    Retorna ``None`` quando o kappa é indefinido (todos os rótulos iguais em
    todos os itens: não há variabilidade para corrigir pelo acaso).
    """

    from statsmodels.stats.inter_rater import aggregate_raters, fleiss_kappa

    if not ratings:
        return None
    categories = sorted({label for row in ratings for label in row})
    index = {label: i for i, label in enumerate(categories)}
    encoded = np.array([[index[label] for label in row] for row in ratings])
    table, _ = aggregate_raters(encoded, n_cat=len(categories))
    if len(categories) < 2:
        return None
    value = fleiss_kappa(table, method="fleiss")
    return None if np.isnan(value) else float(value)


def percent_agreement(ratings: list[list[str]]) -> float | None:
    """% de itens em que todos os avaliadores deram o mesmo rótulo."""

    if not ratings:
        return None
    return sum(len(set(row)) == 1 for row in ratings) / len(ratings)


def read_labels(path: Path, kind: str) -> dict[tuple[str, ...], dict[str, str]]:
    keys = KEY_COLUMNS[kind]
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    labels = {}
    for row in rows:
        key = tuple((row.get(column) or "").strip() for column in keys)
        if key in labels:
            raise ValueError(f"{path.name}: linha duplicada para {key}")
        labels[key] = {k: (v or "").strip().lower() for k, v in row.items()}
    return labels


def load_rater_files(
    directory: Path = VALIDACAO_DIR,
) -> dict[str, dict[str, dict[tuple[str, ...], dict[str, str]]]]:
    """``{avaliador: {"repos": {...}, "releases": {...}}}`` a partir dos CSVs."""

    raters: dict[str, dict[str, Any]] = {}
    for kind in KEY_COLUMNS:
        for path in sorted(directory.glob(f"rotulos_*_{kind}.csv")):
            name = path.stem[len("rotulos_"):-len(f"_{kind}")]
            if name.upper() == "TEMPLATE" or not name:
                continue
            raters.setdefault(name, {})[kind] = read_labels(path, kind)
    incomplete = [n for n, files in raters.items() if set(files) != set(KEY_COLUMNS)]
    if incomplete:
        raise FileNotFoundError(
            "Avaliadores com arquivo faltando (precisa de _repos e _releases): "
            + ", ".join(incomplete)
        )
    return raters


def validate_raters(
    raters: dict[str, dict[str, Any]], partial: bool = False
) -> None:
    """Confere nº de avaliadores, chaves iguais e valores válidos.

    Com ``partial=True`` células vazias são aceitas (rotulagem incompleta):
    esses itens ficam de fora do kappa e do consenso (ver ``build_consensus``).
    """

    if len(raters) < 3:
        raise ValueError(
            f"São necessários 3 avaliadores; encontrados {len(raters)}: "
            f"{', '.join(sorted(raters)) or 'nenhum'}"
        )
    for kind in KEY_COLUMNS:
        key_sets = {name: set(files[kind]) for name, files in raters.items()}
        reference = next(iter(key_sets.values()))
        for name, keys in key_sets.items():
            if keys != reference:
                raise ValueError(
                    f"'{name}' ({kind}) não cobre exatamente os mesmos itens "
                    f"dos demais (faltam {len(reference - keys)}, "
                    f"sobram {len(keys - reference)})."
                )
    for dimension, (kind, column, valid) in DIMENSOES.items():
        for name, files in raters.items():
            for key, row in files[kind].items():
                if partial and not row.get(column):
                    continue
                if row.get(column) not in valid:
                    raise ValueError(
                        f"{name}: valor inválido em '{column}' para {key}: "
                        f"{row.get(column)!r} (válidos: {', '.join(valid)})"
                    )


def majority(labels: list[str]) -> str | None:
    """Rótulo com maioria estrita (>= 2 de 3), ou ``None`` se não houver."""

    label, count = Counter(labels).most_common(1)[0]
    return label if count > len(labels) / 2 else None


def read_tiebreaks(
    directory: Path = VALIDACAO_DIR,
) -> dict[tuple[str, str], tuple[str, str]]:
    """Desempates já decididos: ``{(dimensao, chave): (rotulo_final, justificativa)}``."""

    path = directory / "desempate.csv"
    if not path.exists():
        return {}
    with path.open(newline="", encoding="utf-8") as handle:
        return {
            (r["dimensao"], r["chave"]): (
                (r.get("rotulo_final") or "").strip().lower(),
                (r.get("justificativa") or "").strip(),
            )
            for r in csv.DictReader(handle)
            if (r.get("rotulo_final") or "").strip()
        }


def build_consensus(
    raters: dict[str, dict[str, Any]],
    directory: Path = VALIDACAO_DIR,
    partial: bool = False,
) -> dict[str, Any]:
    """Kappa por dimensão + consenso (maioria; 1-1-1 -> ``desempate.csv``).

    ``partial=True``: usa só os itens que TODOS os avaliadores já rotularam
    (os demais ficam como ``nao_rotulado``). O relatório informa
    ``parcial``, ``n_itens`` e ``n_itens_sem_rotulo_completo`` — declare isso
    no artigo; o sorteio é aleatório, então o subconjunto continua sem viés.
    """

    validate_raters(raters, partial)
    names = sorted(raters)
    tiebreaks = read_tiebreaks(directory)
    report: dict[str, Any] = {
        "avaliadores": names, "parcial": partial, "dimensoes": {},
    }
    consensus_rows: dict[str, list[dict[str, str]]] = {"repos": [], "releases": []}
    no_majority: list[dict[str, str]] = []  # todos os casos sem maioria

    for kind in KEY_COLUMNS:
        keys = sorted(raters[names[0]][kind])
        for key in keys:
            consensus_rows[kind].append(
                {column: value for column, value in zip(KEY_COLUMNS[kind], key)}
            )

    for dimension, (kind, column, _valid) in DIMENSOES.items():
        all_keys = sorted(raters[names[0]][kind])
        labeled = [
            key for key in all_keys
            if all(raters[n][kind][key].get(column) for n in names)
        ]
        keys = labeled if partial else all_keys
        ratings = [[raters[n][kind][key][column] for n in names] for key in keys]
        kappa = fleiss_kappa_from_ratings(ratings)
        report["dimensoes"][dimension] = {
            "n_itens": len(keys),
            "n_itens_sem_rotulo_completo": len(all_keys) - len(labeled),
            "kappa_fleiss": kappa,
            "interpretacao": interpret_kappa(kappa),
            "concordancia_total": percent_agreement(ratings),
            "nota": (
                "kappa indefinido: todos os rótulos iguais em todos os itens"
                if kappa is None and ratings else None
            ),
        }
        rows_by_key = {
            tuple(row[c] for c in KEY_COLUMNS[kind]): row
            for row in consensus_rows[kind]
        }
        for row in rows_by_key.values():
            row.setdefault(column, "")
            row.setdefault(f"{column}_metodo", "nao_rotulado")
            row.setdefault(f"{column}_rotulos", "")
        for key, labels in zip(keys, ratings):
            row = rows_by_key[key]
            final = majority(labels)
            method = "unanimidade" if len(set(labels)) == 1 else "maioria"
            if final is None:
                chave = "|".join(key)
                final, why = tiebreaks.get((dimension, chave), ("", ""))
                method = "desempate" if final else "pendente"
                no_majority.append(
                    {
                        "dimensao": dimension,
                        "chave": chave,
                        "rotulos": "/".join(labels),
                        "rotulo_final": final,
                        "justificativa": why,
                    }
                )
            row[column] = final or ""
            row[f"{column}_metodo"] = method
            row[f"{column}_rotulos"] = "/".join(labels)

    pending = [row for row in no_majority if not row["rotulo_final"]]
    report["casos_sem_maioria"] = len(no_majority)
    report["pendentes_desempate"] = len(pending)
    report["consenso_completo"] = not pending
    return {
        "report": report,
        "consensus": consensus_rows,
        "no_majority": no_majority,
        "pending": pending,
    }


def write_results(result: dict[str, Any], directory: Path = VALIDACAO_DIR) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "concordancia.json").write_text(
        json.dumps(result["report"], ensure_ascii=False, indent=2), encoding="utf-8"
    )
    for kind, rows in result["consensus"].items():
        if not rows:
            continue
        with (directory / f"consenso_{kind}.csv").open(
            "w", newline="", encoding="utf-8"
        ) as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
    if result["no_majority"]:
        # mantém os desempates já decididos (rotulo_final/justificativa)
        with (directory / "desempate.csv").open(
            "w", newline="", encoding="utf-8"
        ) as handle:
            writer = csv.DictWriter(handle, fieldnames=list(result["no_majority"][0]))
            writer.writeheader()
            writer.writerows(result["no_majority"])


def main(directory: Path = VALIDACAO_DIR, partial: bool = False) -> None:
    result = build_consensus(load_rater_files(directory), directory, partial)
    write_results(result, directory)
    print("Avaliadores:", ", ".join(result["report"]["avaliadores"]))
    for name, info in result["report"]["dimensoes"].items():
        kappa = info["kappa_fleiss"]
        shown = "indefinido" if kappa is None else f"{kappa:.3f} ({info['interpretacao']})"
        extra = (
            f" ({info['n_itens_sem_rotulo_completo']} itens sem os 3 rótulos, fora do cálculo)"
            if partial else ""
        )
        print(f"  {name}: kappa de Fleiss = {shown}, n = {info['n_itens']}{extra}")
    if result["pending"]:
        print(
            f"ATENÇÃO: {len(result['pending'])} caso(s) sem maioria — decida em "
            f"reunião e preencha {directory / 'desempate.csv'}; rode de novo."
        )
