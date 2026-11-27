#!/usr/bin/env python3
"""Valida o CSV bruto antes da análise e gera um relatório em Markdown.

Uso:
    python3 validate_data.py --csv ../../dados/raw_full.csv --expected-reps 20 \
        --versions 4.5 5.2 --out ../../dados/relatorio_validacao.md
"""
import argparse
import sys

import numpy as np
import pandas as pd
from scipy import stats

WORKLOADS = ["diffuse", "glass"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--expected-reps", type=int, required=True)
    ap.add_argument("--versions", nargs=2, required=True, metavar=("ANTIGA", "NOVA"))
    ap.add_argument("--out", required=True)
    ap.add_argument("--cv-limit", type=float, default=10.0, help="CV%% máximo aceitável do tempo de render por célula")
    ap.add_argument("--image-tol", type=float, default=0.03,
                    help="diferença relativa máxima do brilho médio da imagem entre versões (mesma cena)")
    args = ap.parse_args()

    cells = [(v, w) for v in args.versions for w in WORKLOADS]
    df = pd.read_csv(args.csv, dtype={"version": str})
    lines, problems = [], []

    def check(ok, msg_ok, msg_bad):
        lines.append(("- [OK] " if ok else "- [PROBLEMA] ") + (msg_ok if ok else msg_bad))
        if not ok:
            problems.append(msg_bad)

    lines.append("# Relatório de validação dos dados\n")
    lines.append(f"Arquivo: `{args.csv}`  |  linhas: {len(df)}\n")
    lines.append("## Verificações\n")

    expected_rows = args.expected_reps * len(cells)
    check(len(df) == expected_rows, f"{len(df)} linhas (esperado {expected_rows})",
          f"{len(df)} linhas, esperado {expected_rows}")

    n_missing = int(df[["render_s", "total_s", "image_mean"]].isna().sum().sum())
    check(n_missing == 0, "sem valores ausentes nas métricas", f"{n_missing} valores ausentes")

    check(bool((df["returncode"] == 0).all()), "todos os processos do Blender terminaram com código 0",
          f"{int((df['returncode'] != 0).sum())} execuções com erro")

    check(bool((df["render_s"] > 0).all()), "todos os tempos de render > 0", "há tempo de render <= 0")

    dup = int(df.duplicated(["phase", "rep", "version", "workload"]).sum())
    check(dup == 0, "sem execuções duplicadas", f"{dup} execuções duplicadas")

    bad_ver = df[df.apply(lambda r: not str(r["blender_version"]).startswith(str(r["version"])), axis=1)]
    check(len(bad_ver) == 0, "a versão real do Blender confere com o rótulo em todas as linhas",
          f"{len(bad_ver)} linhas com blender_version diferente do rótulo")

    for k in ("samples", "threads", "resolution"):
        n = df[k].nunique()
        check(n == 1, f"parâmetro '{k}' constante ({df[k].iloc[0]})", f"parâmetro '{k}' variou ({n} valores)")

    for v, w in cells:
        n = int(((df.version == v) & (df.workload == w)).sum())
        check(n == args.expected_reps, f"Blender {v}/{w}: {n} execuções",
              f"Blender {v}/{w}: {n} execuções (esperado {args.expected_reps})")

    lines.append("\n## Mesma cena nas duas versões? (brilho médio da imagem renderizada)\n")
    lines.append("O Cycles usa a mesma semente, então a imagem deve ser muito parecida entre versões. "
                 "Uma diferença grande indica que as versões não estão renderizando a mesma coisa.\n")
    lines.append("| Carga | " + " | ".join(f"média {v}" for v in args.versions) + " | diferença relativa |")
    lines.append("|---|" + "---|" * (len(args.versions) + 1))
    for w in WORKLOADS:
        ms = [df[(df.version == v) & (df.workload == w)]["image_mean"].mean() for v in args.versions]
        rel = abs(ms[1] - ms[0]) / ms[0] if ms[0] else float("nan")
        lines.append(f"| {w} | " + " | ".join(f"{m:.4f}" for m in ms) + f" | {rel * 100:.2f}% |")
        if not rel <= args.image_tol:
            problems.append(f"carga {w}: brilho médio difere {rel * 100:.1f}% entre versões (> {args.image_tol * 100:.0f}%)")

    lines.append("\n## Variabilidade e outliers por célula (tempo de render, s)\n")
    lines.append("| Versão | Carga | n | média | desvio | CV% | outliers (regra 1,5·IQR) |")
    lines.append("|---|---|---|---|---|---|---|")
    for v, w in cells:
        x = df[(df.version == v) & (df.workload == w)]["render_s"].to_numpy()
        if len(x) == 0:
            continue
        q1, q3 = np.percentile(x, [25, 75])
        iqr = q3 - q1
        out = int(((x < q1 - 1.5 * iqr) | (x > q3 + 1.5 * iqr)).sum())
        cv = x.std(ddof=1) / x.mean() * 100 if len(x) > 1 else float("nan")
        lines.append(f"| {v} | {w} | {len(x)} | {x.mean():.2f} | {x.std(ddof=1):.2f} | {cv:.1f} | {out} |")
        if cv > args.cv_limit:
            problems.append(f"CV de Blender {v}/{w} = {cv:.1f}% (> {args.cv_limit}%): ambiente instável")

    lines.append("\n## Deriva temporal (tempo de render x ordem global de execução)\n")
    lines.append("Correlação de Spearman entre a ordem de execução e o tempo de render, por célula. "
                 "|rho| alto sugere aquecimento ou degradação do computador ao longo da coleta.\n")
    df = df.sort_values("timestamp_utc").reset_index(drop=True)
    df["run_index"] = np.arange(len(df))
    for v, w in cells:
        sub = df[(df.version == v) & (df.workload == w)]
        if len(sub) > 3:
            rho, p = stats.spearmanr(sub["run_index"], sub["render_s"])
            lines.append(f"- Blender {v}/{w}: rho = {rho:.2f} (p = {p:.3f})")

    lines.append("\n## Conclusão\n")
    if problems:
        lines.append("**Há problemas a resolver ou justificar antes da análise:**\n")
        lines += [f"- {p}" for p in problems]
    else:
        lines.append("Nenhum problema encontrado. Dados aptos para análise.")

    with open(args.out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
