#!/usr/bin/env python3
"""Análise estatística do experimento Blender (versão antiga x versão nova), Cycles em CPU.

Uso:
    python3 analyze.py --csv ../../dados/raw_full.csv --versions 4.5 5.2 --out ../../resultados

Gera em --out:
    estatisticas_descritivas.csv, testes.csv, resultados_auto.md,
    boxplot_render.png, render_por_execucao.png, boxplot_total.png

Decisões (justificadas no plano de análise, S1):
  - Métrica primária: tempo de render (s), um teste por carga de trabalho, alfa corrigido por Bonferroni (m = 2).
    MENOR é MELHOR (diferença negativa = versão nova mais rápida).
  - Métrica secundária (exploratória, sem correção): tempo total do processo (inclui abrir o Blender e montar a cena).
  - Teste: t de Welch se ambos os grupos passam no Shapiro-Wilk (p > 0,05); senão Mann-Whitney U.
  - Tamanho do efeito: g de Hedges e delta de Cliff; IC 95% bootstrap da diferença percentual de médias.
  - Simulação (reaproveitando o Lab04): erro tipo I e poder do teste com a variância observada.
"""
import argparse
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

ALPHA = 0.05
WORKLOADS = [("diffuse", "Cena difusa (4 rebatimentos)"), ("glass", "Cena com vidro e metal (12 rebatimentos)")]
METRICS = [("render_s", "Tempo de render (s)", "primária"), ("total_s", "Tempo total do processo (s)", "secundária")]


def hedges_g(a, b):
    """Diferença padronizada (b - a). Negativo = b menor (mais rápido)."""
    na, nb = len(a), len(b)
    sp = np.sqrt(((na - 1) * np.var(a, ddof=1) + (nb - 1) * np.var(b, ddof=1)) / (na + nb - 2))
    d = (np.mean(b) - np.mean(a)) / sp
    j = 1 - 3 / (4 * (na + nb) - 9)
    return d * j


def cliffs_delta(a, b):
    a, b = np.asarray(a), np.asarray(b)
    gt = (b[:, None] > a[None, :]).sum()
    lt = (b[:, None] < a[None, :]).sum()
    return (gt - lt) / (len(a) * len(b))


def label_g(g):
    g = abs(g)
    return "desprezível" if g < 0.2 else "pequeno" if g < 0.5 else "médio" if g < 0.8 else "grande"


def label_cliff(d):
    d = abs(d)
    return "desprezível" if d < 0.147 else "pequeno" if d < 0.33 else "médio" if d < 0.474 else "grande"


def boot_pct_diff(a, b, n_boot=10000, seed=1):
    rng = np.random.default_rng(seed)
    a, b = np.asarray(a), np.asarray(b)
    diffs = np.empty(n_boot)
    for i in range(n_boot):
        ma = rng.choice(a, len(a), replace=True).mean()
        mb = rng.choice(b, len(b), replace=True).mean()
        diffs[i] = (mb - ma) / ma * 100
    return np.percentile(diffs, [2.5, 97.5])


def simulate(sd, n, delta, n_sim=2000, seed=7):
    """Taxa de rejeição do t de Welch com diferença verdadeira = delta (delta=0 -> erro tipo I)."""
    rng = np.random.default_rng(seed)
    rej = 0
    for _ in range(n_sim):
        x = rng.normal(0, sd, n)
        y = rng.normal(delta, sd, n)
        if stats.ttest_ind(x, y, equal_var=False).pvalue < ALPHA:
            rej += 1
    return rej / n_sim


def md_table(headers, rows):
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--versions", nargs=2, required=True, metavar=("ANTIGA", "NOVA"),
                    help="rótulos das versões como aparecem no CSV; a primeira é a referência")
    ap.add_argument("--phase", default="full", choices=["full", "pilot"],
                    help="'pilot' serve só para testar o fluxo; resultados do piloto não entram no relatório")
    args = ap.parse_args()
    old, new = args.versions
    os.makedirs(args.out, exist_ok=True)

    df = pd.read_csv(args.csv, dtype={"version": str})
    df = df[df["phase"] == args.phase].copy()
    if df.empty:
        print(f"Nenhuma linha com phase == '{args.phase}'.", file=sys.stderr)
        return 1

    alpha_adj = ALPHA / len(WORKLOADS)
    desc_rows, test_rows, md = [], [], []

    for wk, wk_name in WORKLOADS:
        for m, m_name, kind in METRICS:
            a = df[(df.workload == wk) & (df.version == old)][m].to_numpy()
            b = df[(df.workload == wk) & (df.version == new)][m].to_numpy()
            for v, x in ((old, a), (new, b)):
                desc_rows.append({
                    "carga": wk, "metrica": m, "versao": v, "n": len(x),
                    "media": x.mean(), "desvio": x.std(ddof=1), "mediana": np.median(x),
                    "q1": np.percentile(x, 25), "q3": np.percentile(x, 75),
                    "min": x.min(), "max": x.max(), "cv_pct": x.std(ddof=1) / x.mean() * 100,
                })
            sh_a, sh_b = stats.shapiro(a).pvalue, stats.shapiro(b).pvalue
            normal = sh_a > ALPHA and sh_b > ALPHA
            if normal:
                p = stats.ttest_ind(a, b, equal_var=False).pvalue
                test_name = "t de Welch"
            else:
                p = stats.mannwhitneyu(a, b, alternative="two-sided").pvalue
                test_name = "Mann-Whitney U"
            g = hedges_g(a, b)
            cd = cliffs_delta(a, b)
            lo, hi = boot_pct_diff(a, b)
            pct = (b.mean() - a.mean()) / a.mean() * 100
            thr = alpha_adj if kind == "primária" else ALPHA
            test_rows.append({
                "carga": wk, "metrica": m, "tipo": kind, "teste": test_name,
                "shapiro_p_antiga": sh_a, "shapiro_p_nova": sh_b, "p_valor": p, "limiar_alfa": thr,
                "significativo": p < thr, "dif_pct_medias": pct,
                "ic95_boot_lo": lo, "ic95_boot_hi": hi,
                "hedges_g": g, "hedges_g_classe": label_g(g),
                "cliffs_delta": cd, "cliffs_classe": label_cliff(cd),
            })

    desc = pd.DataFrame(desc_rows)
    tests = pd.DataFrame(test_rows)
    desc.to_csv(os.path.join(args.out, "estatisticas_descritivas.csv"), index=False)
    tests.to_csv(os.path.join(args.out, "testes.csv"), index=False)

    sim_rows = []
    for wk, _ in WORKLOADS:
        a = df[(df.workload == wk) & (df.version == old)]["render_s"].to_numpy()
        b = df[(df.workload == wk) & (df.version == new)]["render_s"].to_numpy()
        sd = np.sqrt((a.var(ddof=1) + b.var(ddof=1)) / 2)
        n = min(len(a), len(b))
        sim_rows.append({
            "carga": wk, "n_por_grupo": n, "desvio_comum": sd,
            "erro_tipo_I_simulado": simulate(sd, n, 0.0),
            "poder_para_diferenca_observada": simulate(sd, n, abs(b.mean() - a.mean())),
            "poder_para_diferenca_de_3pct": simulate(sd, n, 0.03 * a.mean()),
        })
    sim = pd.DataFrame(sim_rows)

    md.append(f"# Resultados da análise: Blender {old} (referência) x {new} (gerado por analyze.py)\n")
    md.append(f"Execuções analisadas: {len(df)} (fase `{args.phase}`). Alfa = {ALPHA}; para a métrica primária "
              f"(tempo de render), alfa ajustado por Bonferroni = {alpha_adj:.3f}. "
              f"**Menor tempo é melhor: diferença negativa significa que o Blender {new} é mais rápido.**\n")
    for wk, wk_name in WORKLOADS:
        md.append(f"## {wk_name}\n")
        sub = desc[desc.carga == wk]
        md.append("### Estatística descritiva\n")
        md.append(md_table(
            ["Métrica", "Versão", "n", "Média", "Desvio", "Mediana", "Q1", "Q3", "Mín", "Máx", "CV%"],
            [[r.metrica, r.versao, r.n, f"{r.media:.3f}", f"{r.desvio:.3f}", f"{r.mediana:.3f}",
              f"{r.q1:.3f}", f"{r.q3:.3f}", f"{r['min']:.3f}", f"{r['max']:.3f}", f"{r.cv_pct:.1f}"]
             for _, r in sub.iterrows()]))
        md.append("\n### Testes de hipótese e tamanho do efeito\n")
        st = tests[tests.carga == wk]
        md.append(md_table(
            ["Métrica", "Tipo", "Teste", "p", "Limiar", "Signif.", f"Dif. % ({new} vs {old})", "IC95% (bootstrap)",
             "Hedges g", "Cliff δ"],
            [[r.metrica, r.tipo, r.teste, f"{r.p_valor:.4g}", f"{r.limiar_alfa:.3f}",
              "sim" if r.significativo else "não", f"{r.dif_pct_medias:+.2f}%",
              f"[{r.ic95_boot_lo:+.2f}%; {r.ic95_boot_hi:+.2f}%]",
              f"{r.hedges_g:+.2f} ({r.hedges_g_classe})", f"{r.cliffs_delta:+.2f} ({r.cliffs_classe})"]
             for _, r in st.iterrows()]))
        md.append("")
    md.append("## Simulação de erro tipo I e poder (tempo de render)\n")
    md.append(md_table(
        ["Carga", "n/grupo", "Desvio comum (s)", "Erro tipo I simulado", "Poder (dif. observada)", "Poder (dif. 3%)"],
        [[r.carga, r.n_por_grupo, f"{r.desvio_comum:.3f}", f"{r.erro_tipo_I_simulado:.3f}",
          f"{r.poder_para_diferenca_observada:.2f}", f"{r.poder_para_diferenca_de_3pct:.2f}"]
         for _, r in sim.iterrows()]))
    md.append("\nFiguras: `boxplot_render.png`, `render_por_execucao.png`, `boxplot_total.png`.")
    with open(os.path.join(args.out, "resultados_auto.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")

    colors = {old: "#9aa5b1", new: "#1f6feb"}
    for m, title, fname in (("render_s", "Tempo de render (s) por versão", "boxplot_render.png"),
                            ("total_s", "Tempo total do processo (s) por versão", "boxplot_total.png")):
        fig, axes = plt.subplots(1, 2, figsize=(9, 4))
        for ax, (wk, wk_name) in zip(axes, WORKLOADS):
            data = [df[(df.workload == wk) & (df.version == v)][m].to_numpy() for v in (old, new)]
            bp = ax.boxplot(data, tick_labels=[f"Blender {old}", f"Blender {new}"], patch_artist=True, showfliers=False)
            for patch, v in zip(bp["boxes"], (old, new)):
                patch.set_facecolor(colors[v]); patch.set_alpha(0.6)
            for i, d in enumerate(data, start=1):
                ax.scatter(np.random.default_rng(i).normal(i, 0.04, len(d)), d, s=12, color="black", alpha=0.6)
            ax.set_title(wk_name, fontsize=10)
            ax.set_ylabel(title)
        fig.suptitle(title)
        fig.tight_layout()
        fig.savefig(os.path.join(args.out, fname), dpi=150)
        plt.close(fig)

    df = df.sort_values("timestamp_utc").reset_index(drop=True)
    df["run_index"] = np.arange(1, len(df) + 1)
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    for ax, (wk, wk_name) in zip(axes, WORKLOADS):
        for v in (old, new):
            s = df[(df.workload == wk) & (df.version == v)]
            ax.plot(s["run_index"], s["render_s"], marker="o", ms=4, lw=1, color=colors[v], label=f"Blender {v}")
        ax.set_title(wk_name, fontsize=10)
        ax.set_xlabel("ordem global de execução")
        ax.set_ylabel("tempo de render (s)")
        ax.legend()
    fig.suptitle("Tempo de render ao longo da coleta (checagem de deriva temporal)")
    fig.tight_layout()
    fig.savefig(os.path.join(args.out, "render_por_execucao.png"), dpi=150)
    plt.close(fig)

    print(open(os.path.join(args.out, "resultados_auto.md"), encoding="utf-8").read())
    return 0


if __name__ == "__main__":
    sys.exit(main())
