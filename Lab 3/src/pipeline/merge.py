"""Junta caches de coletas feitas em máquinas diferentes (``--shard I/N``).

Cada integrante coleta uma fatia dos candidatos com o PRÓPRIO token (cota de
5.000 req/h por token). No fim, as pastas ``data/cache`` são reunidas em uma
só. Como os arquivos são por repositório, não há conflito de conteúdo — só é
preciso escolher a melhor cópia quando o mesmo repositório existe em mais de
uma pasta (ex.: o cache da S01, só com metadados, e o da S02, completo).
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any


def _parts(path: Path) -> Path:
    """Pasta com os intervalos grandes (runs, compare) do repositório."""

    return path.with_name(path.stem + ".parts")


def _size(path: Path) -> int:
    size = path.stat().st_size
    parts = _parts(path)
    if parts.is_dir():
        size += sum(f.stat().st_size for f in parts.rglob("*.json"))
    return size


def _rank(path: Path) -> tuple[int, int, int]:
    """Melhor cópia: tem decisão > mais etapas em cache > mais dados."""

    try:
        record: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return (-1, 0, 0)
    pipeline = record.get("_pipeline_cache") or {}
    return ("decision" in pipeline, len(pipeline), _size(path))  # type: ignore[return-value]


def merge_caches(sources: list[Path], destination: Path) -> dict[str, int]:
    """Copia para ``destination`` a melhor versão de cada ``*.json`` das fontes."""

    destination.mkdir(parents=True, exist_ok=True)
    stats = {"copied": 0, "kept": 0, "invalid": 0}
    for source in sources:
        for path in sorted(Path(source).glob("*.json")):
            if path.name.startswith("_"):
                continue
            rank = _rank(path)
            if rank[0] == -1:
                stats["invalid"] += 1
                continue
            target = destination / path.name
            if target.exists() and target.resolve() == path.resolve():
                continue
            if target.exists() and _rank(target) >= rank:
                stats["kept"] += 1
                continue
            shutil.copyfile(path, target)
            if _parts(target).exists():
                shutil.rmtree(_parts(target))
            if _parts(path).is_dir():
                shutil.copytree(_parts(path), _parts(target))
            stats["copied"] += 1
    return stats
