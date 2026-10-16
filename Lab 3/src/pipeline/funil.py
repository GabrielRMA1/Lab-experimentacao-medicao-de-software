"""Funil de seleção (seção 7): quantos repositórios restaram em cada etapa."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from src.pipeline.config import Config
from src.pipeline.selecao import POUCAS_RELEASES, POUCOS_RUNS, SEM_ACTIONS


def select_final_sample(
    candidates: list[dict[str, Any]],
    decisions: dict[str, dict[str, Any]],
    cfg: Config,
) -> list[str]:
    """Aceitos (decisão válida para a configuração atual), por estrelas, até o teto."""

    signature = cfg.window_signature()
    accepted = [
        c for c in candidates
        if (decisions.get(c["full_name"]) or {}).get("status") == "accepted"
        and decisions[c["full_name"]].get("config") == signature
    ]
    accepted.sort(key=lambda c: c.get("stargazers_count") or 0, reverse=True)
    return [c["full_name"] for c in accepted[: cfg.sample_target]]


def build_funnel(
    candidates: list[dict[str, Any]],
    decisions: dict[str, dict[str, Any]],
    cfg: Config,
) -> dict[str, Any]:
    signature = cfg.window_signature()
    valid = {
        name: d for name, d in decisions.items()
        if d.get("config") == signature
    }
    n_candidates = len(candidates)
    names = {c["full_name"] for c in candidates}
    evaluated = {n: d for n, d in valid.items() if n in names}
    by_reason: dict[str, int] = {}
    for decision in evaluated.values():
        if decision["status"] == "discarded":
            by_reason[decision["reason"]] = by_reason.get(decision["reason"], 0) + 1
    errors = sum(1 for d in evaluated.values() if d["status"] == "error")

    n_eval = len(evaluated)
    n_actions = n_eval - by_reason.get(SEM_ACTIONS, 0)
    n_releases = n_actions - by_reason.get(POUCAS_RELEASES, 0)
    n_runs = n_releases - by_reason.get(POUCOS_RUNS, 0)
    final = select_final_sample(candidates, valid, cfg)

    stages = [
        {"etapa": "Candidatos (busca por estrelas)", "n": n_candidates,
         "descartados": 0, "motivo": None},
        {"etapa": "Avaliados pela coleta", "n": n_eval,
         "descartados": n_candidates - n_eval,
         "motivo": "Não avaliados: coleta encerrada ao atingir a cota da amostra"},
        {"etapa": "Com GitHub Actions", "n": n_actions,
         "descartados": by_reason.get(SEM_ACTIONS, 0),
         "motivo": "Sem workflows (total_count = 0)"},
        {"etapa": f"≥ {cfg.min_releases} releases estáveis na janela", "n": n_releases,
         "descartados": by_reason.get(POUCAS_RELEASES, 0),
         "motivo": f"Menos de {cfg.min_releases} releases (draft=false, prerelease=false) na janela"},
        {"etapa": f"≥ {cfg.min_runs} workflow runs válidos na janela", "n": n_runs,
         "descartados": by_reason.get(POUCOS_RUNS, 0),
         "motivo": (f"Menos de {cfg.min_runs} runs (push, default branch, "
                    "success/failure) na janela")},
        {"etapa": "Amostra final", "n": len(final),
         "descartados": n_runs - len(final),
         "motivo": f"Acima do teto de {cfg.sample_target} (maiores por estrelas ficam)"},
    ]
    return {
        "janela": {"inicio": cfg.observation_start, "fim": cfg.observation_end},
        "criterios": {"min_releases": cfg.min_releases, "min_runs": cfg.min_runs},
        "etapas": stages,
        "erros_pendentes": errors,
        "amostra_final": len(final),
        "atinge_minimo": len(final) >= cfg.min_sample,
        "minimo_exigido": cfg.min_sample,
        "repositorios_amostra_final": final,
    }


def to_markdown(funnel: dict[str, Any]) -> str:
    lines = [
        "| Etapa | Repositórios | Descartados | Motivo |",
        "|---|---:|---:|---|",
    ]
    for stage in funnel["etapas"]:
        lines.append(
            f"| {stage['etapa']} | {stage['n']} | {stage['descartados']} | "
            f"{stage['motivo'] or '—'} |"
        )
    if funnel["erros_pendentes"]:
        lines.append(f"\n> {funnel['erros_pendentes']} repositório(s) com erro de "
                     "coleta pendente(s); rode `collect` de novo.")
    if not funnel["atinge_minimo"]:
        lines.append(f"\n> ATENÇÃO: amostra final ({funnel['amostra_final']}) abaixo "
                     f"do mínimo de {funnel['minimo_exigido']}.")
    return "\n".join(lines) + "\n"


def _tex(text: str) -> str:
    return text.replace("≥", "$\\geq$").replace("%", "\\%")


def to_latex(funnel: dict[str, Any]) -> str:
    rows = "\n".join(
        _tex(s["etapa"]) + " & " + str(s["n"]) + " & " + str(s["descartados"]) + " \\\\"
        for s in funnel["etapas"]
    )
    return (
        "\\begin{table}[ht]\n\\centering\n"
        "\\caption{Funil de seleção dos repositórios}\n\\label{tab:funil}\n"
        "\\begin{tabular}{lrr}\n\\hline\n"
        "Etapa & Repositórios & Descartados \\\\\n\\hline\n"
        + rows
        + "\n\\hline\n\\end{tabular}\n\\end{table}\n"
    )


def write_funnel(
    funnel: dict[str, Any],
    candidates: list[dict[str, Any]],
    decisions: dict[str, dict[str, Any]],
    data_dir: Path,
) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "funil.json").write_text(
        json.dumps(funnel, ensure_ascii=False, indent=2), encoding="utf-8")
    (data_dir / "funil.md").write_text(to_markdown(funnel), encoding="utf-8")
    (data_dir / "funil_tabela.tex").write_text(to_latex(funnel), encoding="utf-8")
    final = set(funnel["repositorios_amostra_final"])
    with (data_dir / "selecao_repositorios.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.writer(handle)
        writer.writerow(["full_name", "estrelas", "situacao", "etapa", "motivo"])
        for c in candidates:
            d = decisions.get(c["full_name"])
            if c["full_name"] in final:
                situacao = "amostra_final"
            elif d is None:
                situacao = "nao_avaliado"
            else:
                situacao = {"accepted": "aceito_fora_do_teto"}.get(d["status"], d["status"])
            writer.writerow([c["full_name"], c.get("stargazers_count"), situacao,
                             (d or {}).get("stage"), (d or {}).get("reason")])
