"""Heurística de *release corretiva* (RQ 03b) — versões testáveis.

Uma release corretiva é aquela cujo objetivo principal é corrigir um defeito
recente. O enunciado sugere duas pistas automáticas:

1. a versão muda apenas no número de *patch* (``2.3.0 → 2.3.1``); e/ou
2. há commits com ``revert``, ``hotfix`` ou ``fix`` na mensagem.

Aqui elas são combinadas em **versões nomeadas** (``VERSIONS``). Cada versão é
avaliada contra a amostra-ouro (precisão/recall/F1 — ver
``src/validacao/avaliar_heuristica.py``) e o grupo escolhe/refina a melhor,
documentando cada tentativa em ``docs/HEURISTICA_CORRETIVA.md``.

Módulo de cálculo puro: não acessa a API do GitHub.
"""

from __future__ import annotations

import re
from typing import Any, Callable

DEFAULT_VERSION = "v3_patch_ou_palavras"

_VERSION_RE = re.compile(r"(\d+)\.(\d+)(?:\.(\d+))?")
_FIX_RE = re.compile(
    r"\b(revert(?:s|ed|ing)?|hotfix(?:es)?|bug-?fix(?:es)?|fix(?:es|ed|ing)?)\b",
    re.IGNORECASE,
)
_NOTES_RE = re.compile(
    r"\b(hotfix|regression|revert(?:ed)?|emergency|patch release|"
    r"bug-?fix release)\b",
    re.IGNORECASE,
)

KW_RATIO_MIN = 0.5  # fração de commits "de correção" para v2


def parse_version(tag: str | None) -> tuple[int, int, int] | None:
    """Extrai ``(major, minor, patch)`` de uma tag (``v1.2.3``, ``rel-1.2``).

    Retorna ``None`` se não houver versão ou se parecer versionamento por
    calendário (``2024.05.10``), onde "patch" não tem o significado SemVer.
    """

    if not tag:
        return None
    match = _VERSION_RE.search(tag)
    if not match:
        return None
    major, minor, patch = (int(g) if g is not None else 0 for g in match.groups())
    if major > 999:
        return None
    return major, minor, patch


def is_patch_bump(previous_tag: str | None, tag: str | None) -> bool:
    """``True`` se só o patch cresceu em relação à release imediatamente anterior."""

    previous, current = parse_version(previous_tag), parse_version(tag)
    if previous is None or current is None:
        return False
    return previous[:2] == current[:2] and current[2] > previous[2]


def fix_keyword_ratio(commits: list[dict[str, Any]]) -> float:
    """Fração de commits cuja 1ª linha casa com revert/hotfix/fix."""

    if not commits:
        return 0.0
    hits = sum(1 for c in commits if _FIX_RE.search(c.get("message") or ""))
    return hits / len(commits)


def notes_have_keyword(release: dict[str, Any]) -> bool:
    """Palavras de emergência no título ou no início das notas da release."""

    text = f"{release.get('name') or ''}\n{(release.get('body') or '')[:300]}"
    return bool(_NOTES_RE.search(text))


def extract_features(
    release: dict[str, Any],
    previous_release: dict[str, Any] | None,
    commits: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "patch_bump": is_patch_bump(
            (previous_release or {}).get("tag_name"), release.get("tag_name")
        ),
        "kw_ratio": fix_keyword_ratio(commits),
        "kw_any": any(_FIX_RE.search(c.get("message") or "") for c in commits),
        "n_commits": len(commits),
        "notes_kw": notes_have_keyword(release),
    }


def _v1(f): return f["patch_bump"]
def _v2(f): return f["n_commits"] > 0 and f["kw_ratio"] >= KW_RATIO_MIN
def _v3(f): return _v1(f) or _v2(f)
def _v4(f): return f["patch_bump"] and f["kw_any"]


def _v5(f):
    """Refinada: patch com algum sinal de correção, release 'só de fixes'
    pequena, ou notas que falam de hotfix/regressão/revert."""
    return (
        (f["patch_bump"] and (f["kw_ratio"] >= 0.25 or f["notes_kw"]))
        or (f["n_commits"] > 0 and f["kw_ratio"] >= KW_RATIO_MIN
            and f["n_commits"] <= 30)
        or f["notes_kw"]
    )


VERSIONS: dict[str, Callable[[dict[str, Any]], bool]] = {
    "v1_patch": _v1,
    "v2_palavras": _v2,
    "v3_patch_ou_palavras": _v3,
    "v4_patch_e_palavras": _v4,
    "v5_refinada": _v5,
}


def is_corrective(
    release: dict[str, Any],
    previous_release: dict[str, Any] | None,
    commits: list[dict[str, Any]],
    version: str = DEFAULT_VERSION,
) -> bool:
    """Aplica a versão ``version`` da heurística a uma release."""

    if version not in VERSIONS:
        raise KeyError(
            f"Versão de heurística desconhecida: {version!r}. "
            f"Opções: {', '.join(VERSIONS)}"
        )
    return bool(VERSIONS[version](extract_features(release, previous_release, commits)))


def classify_releases(
    releases_sorted: list[dict[str, Any]],
    commits_by_tag: dict[str, list[dict[str, Any]]],
    version: str = DEFAULT_VERSION,
) -> list[dict[str, Any]]:
    """Marca cada release (ordem cronológica) como corretiva ou não.

    ``releases_sorted``: releases estáveis, da mais antiga à mais nova (todo o
    histórico coletado). ``commits_by_tag[tag]``: commits que entraram em
    ``tag`` em relação à release anterior (do cache ``compare_v1``). A
    primeira release da história não tem anterior: nunca é corretiva por
    "patch", e sem commits só as notas podem marcá-la.
    """

    classified = []
    previous: dict[str, Any] | None = None
    for release in releases_sorted:
        commits = commits_by_tag.get(release.get("tag_name"), [])
        classified.append(
            {
                "tag_name": release.get("tag_name"),
                "published_at": release.get("published_at"),
                "is_corrective": is_corrective(release, previous, commits, version),
            }
        )
        previous = release
    return classified
