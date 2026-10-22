"""Dataset sintético (80 repositórios) para testar as análises sem coletar nada."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.pipeline.dicionario import COLUMN_NAMES

N = 80
TIPOS = ["biblioteca_framework", "aplicacao_servico", "ferramenta_cli"]


def dataset_sintetico(seed: int = 1) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    n_rel = rng.integers(5, 300, N)
    semanas = 365.25 / 7
    linhas = []
    for i in range(N):
        linhas.append({c: None for c in COLUMN_NAMES} | {
            "full_name": f"org/repo{i}", "html_url": f"https://github.com/org/repo{i}",
            "language": ["Python", "Go", "TypeScript", "Rust", "Java", "C", None][i % 7],
            "stars": int(rng.integers(1000, 100000)), "forks": 1,
            "contributors": int(rng.integers(5, 2000)), "created_at": "2018-01-01T00:00:00Z",
            "idade_dias_fim_janela": int(rng.integers(400, 5000)), "default_branch": "main",
            "n_releases": int(n_rel[i]), "n_prereleases_janela": int(rng.integers(0, 30)),
            "deploy_freq_semana": n_rel[i] / semanas,
            "lt_release_mediana_h": float(rng.lognormal(5, 1.5)),
            "lt_commit_mediana_h": float(rng.lognormal(4, 1.2)),
            "ci_n_sucessos": int(rng.integers(50, 500)), "ci_n_falhas": int(rng.integers(0, 100)),
            "cfr_ci": float(rng.uniform(0, 0.6)),
            "cfr_entrega": None if i == 0 else float(rng.uniform(0, 0.5)),
            "rework_rate": float(rng.uniform(0, 0.5)),
            "rec_mediana_h": None if i == 1 else float(rng.lognormal(2, 1.5)),
            "rec_n_episodios": 10, "rec_n_censurados": 1, "rec_prop_censurados": 0.1,
            "cfr_n_avaliadas": 20, "cfr_n_censuradas": 1, "lt_n_releases_compare_404": 0,
            "runs_intervalos_truncados": 0,
        })
    return pd.DataFrame(linhas, columns=COLUMN_NAMES)


def preparar_ambiente(pasta: Path) -> tuple[Path, Path, Path]:
    """CSV sintético + consenso de tipo do projeto (60 repos) numa pasta temporária."""

    csv = pasta / "dataset_repos.csv"
    dataset_sintetico().to_csv(csv, index=False)
    validacao = pasta / "validacao"
    validacao.mkdir()
    pd.DataFrame({"full_name": [f"org/repo{i}" for i in range(60)],
                  "tipo_projeto": [TIPOS[i % 3] for i in range(60)]}).to_csv(
        validacao / "consenso_repos.csv", index=False)
    saida = pasta / "resultados"
    saida.mkdir()
    return csv, saida, validacao
