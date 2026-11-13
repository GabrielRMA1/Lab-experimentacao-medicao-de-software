import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ALFA = 0.05
N = 30
SEMENTE = 42

BASE_DIR = Path(__file__).resolve().parent
CAMINHO_DADOS = BASE_DIR / "data" / "prs.csv"
CAMINHO_SIMULADOS = BASE_DIR / "data" / "simulados.csv"
CAMINHO_RESULTADOS = BASE_DIR / "data" / "resultados.json"

rng = np.random.default_rng(SEMENTE)


def parametros(tempos):
    """Calcula a mediana e o desvio-padrão amostral dos logaritmos."""
    mediana = float(np.median(tempos))
    sigma = float(np.std(np.log(tempos), ddof=1))
    return mediana, sigma


def simular(tempos, n=N):
    """Gera tempos sintéticos por uma distribuição lognormal."""
    mediana, sigma = parametros(tempos)
    return rng.lognormal(np.log(mediana), sigma, n)


def main():
    reais = pd.read_csv(CAMINHO_DADOS)
    reais = reais[reais["tempo_merge_horas"] > 0].copy()

    com_bot = reais.loc[
        reais["grupo"] == "com_bot", "tempo_merge_horas"
    ].to_numpy(dtype=float)
    sem_bot = reais.loc[
        reais["grupo"] == "sem_bot", "tempo_merge_horas"
    ].to_numpy(dtype=float)

    if len(com_bot) < 2 or len(sem_bot) < 2:
        raise ValueError("Cada grupo precisa ter pelo menos dois tempos positivos.")

    sim_com = simular(com_bot)
    sim_sem = simular(sem_bot)

    welch = stats.ttest_ind(sim_com, sim_sem, equal_var=False)
    mann_whitney = stats.mannwhitneyu(
        sim_com, sim_sem, alternative="two-sided"
    )

    simulados = pd.DataFrame({
        "grupo": ["com_bot"] * N + ["sem_bot"] * N,
        "tempo_merge_horas": np.concatenate([sim_com, sim_sem]),
    })
    simulados.to_csv(CAMINHO_SIMULADOS, index=False)

    resultados = {
        "alfa": ALFA,
        "n": N,
        "semente": SEMENTE,
        "welch_t": float(welch.statistic),
        "welch_gl": float(welch.df),
        "welch_p": float(welch.pvalue),
        "mw_u": float(mann_whitney.statistic),
        "mw_p": float(mann_whitney.pvalue),
    }
    with CAMINHO_RESULTADOS.open("w", encoding="utf-8") as arquivo:
        json.dump(resultados, arquivo, indent=2, ensure_ascii=False)

    print("Dados reais:")
    for nome, tempos in (("Com bot", com_bot), ("Sem bot", sem_bot)):
        mediana, sigma = parametros(tempos)
        print(
            f"{nome}: n={len(tempos)}, média={np.mean(tempos):.2f} h, "
            f"mediana={mediana:.2f} h, sigma={sigma:.2f}"
        )
    print("\nResultados dos testes:")
    print(json.dumps(resultados, indent=2, ensure_ascii=False))
    print(f"\nArquivos gerados: {CAMINHO_SIMULADOS} e {CAMINHO_RESULTADOS}")


if __name__ == "__main__":
    main()
