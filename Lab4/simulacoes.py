import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

SEMENTE = 42
REPETICOES = 10_000
ALFAS = (0.05, 0.01)

REDUCOES = (0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9)

PROP_OUTLIERS = 0.05
ATRASO_OUTLIER_H = 2000.0

BASE_DIR = Path(__file__).resolve().parent
CAMINHO_DADOS = BASE_DIR / "data" / "prs.csv"
CAMINHO_SIMULACOES = BASE_DIR / "data" / "simulacoes.csv"
CAMINHO_PODER_N = BASE_DIR / "data" / "poder_por_n.csv"
CAMINHO_REAIS = BASE_DIR / "data" / "reais_resultados.json"

SITUACOES = [
    ("A", "Normal: log do tempo (pressupostos OK)", 30, "log"),
    ("B", "Lognormal: tempo em horas (assimétrico)", 30, "horas"),
    ("C", "Lognormal: amostra pequena", 10, "horas"),
    ("D", "Lognormal + 5% de outliers extremos", 30, "outliers"),
]


def carregar_reais():
    reais = pd.read_csv(CAMINHO_DADOS)
    reais = reais[reais["tempo_merge_horas"] > 0]
    com = reais.loc[reais["grupo"] == "com_bot", "tempo_merge_horas"].to_numpy(float)
    sem = reais.loc[reais["grupo"] == "sem_bot", "tempo_merge_horas"].to_numpy(float)
    return com, sem


def parametros_base(sem_bot, com_bot):
    """Mediana do grupo sem bot e sigma (log) combinado dos dois grupos."""
    mediana = float(np.median(sem_bot))
    s1 = np.std(np.log(sem_bot), ddof=1)
    s2 = np.std(np.log(com_bot), ddof=1)
    sigma = float(np.sqrt((s1**2 + s2**2) / 2))
    return mediana, sigma


def gerar(rng, n, reducao, mediana, sigma, tipo):
    """Gera REPETICOES conjuntos de dados (linhas) para os dois grupos."""
    mu_sem = np.log(mediana)
    mu_com = np.log(mediana * (1 - reducao))
    sem = rng.lognormal(mu_sem, sigma, (REPETICOES, n))
    com = rng.lognormal(mu_com, sigma, (REPETICOES, n))
    if tipo == "log":
        return np.log(com), np.log(sem)
    if tipo == "outliers":
        for grupo in (com, sem):
            mascara = rng.random(grupo.shape) < PROP_OUTLIERS
            grupo[mascara] += ATRASO_OUTLIER_H
    return com, sem


def pvalores(com, sem):
    p_welch = stats.ttest_ind(com, sem, equal_var=False, axis=1).pvalue
    p_mw = stats.mannwhitneyu(com, sem, alternative="two-sided", axis=1).pvalue
    return p_welch, p_mw


def rodar_simulacoes(mediana, sigma):
    sementes = np.random.SeedSequence(SEMENTE).spawn(len(SITUACOES))
    linhas = []
    for (sid, nome, n, tipo), semente in zip(SITUACOES, sementes):
        rng = np.random.default_rng(semente)
        for reducao in REDUCOES:
            com, sem = gerar(rng, n, reducao, mediana, sigma, tipo)
            p_welch, p_mw = pvalores(com, sem)
            for teste, p in (("t de Welch", p_welch), ("Mann-Whitney", p_mw)):
                for alfa in ALFAS:
                    taxa = float(np.mean(p < alfa))
                    linhas.append({
                        "situacao": sid,
                        "nome_situacao": nome,
                        "n": n,
                        "reducao_mediana": reducao,
                        "teste": teste,
                        "alfa": alfa,
                        "taxa_rejeicao": taxa,
                        "erro_padrao": float(np.sqrt(taxa * (1 - taxa) / REPETICOES)),
                    })
        print(f"Situação {sid} concluída ({nome})")
    return pd.DataFrame(linhas)


def rodar_poder_por_n(mediana, sigma, razao, tamanhos=(10, 30, 100, 300, 1000, 2000)):
    """Poder na situação B (lognormal, horas) para o efeito observado nos dados reais.

    O efeito é a razão entre as médias geométricas (deslocamento no log), que é o
    parâmetro de um modelo lognormal com o mesmo sigma nos dois grupos.
    Para n grandes, usa menos repetições para caber na memória.
    """
    rng = np.random.default_rng(SEMENTE + 1)
    linhas = []
    for n in tamanhos:
        reps = REPETICOES if n <= 300 else 2_000
        mu_sem = np.log(mediana)
        sem = rng.lognormal(mu_sem, sigma, (reps, n))
        com = rng.lognormal(mu_sem + np.log(razao), sigma, (reps, n))
        p_welch, p_mw = pvalores(com, sem)
        for teste, p in (("t de Welch", p_welch), ("Mann-Whitney", p_mw)):
            linhas.append({"n": n, "teste": teste, "repeticoes": reps,
                           "poder": float(np.mean(p < 0.05))})
    return pd.DataFrame(linhas)


def analisar_reais(com, sem):
    """Aplica os dois testes aos dados reais e calcula tamanhos de efeito."""
    n1, n2 = len(com), len(sem)
    welch = stats.ttest_ind(com, sem, equal_var=False)
    mw = stats.mannwhitneyu(com, sem, alternative="two-sided")
    welch_log = stats.ttest_ind(np.log(com), np.log(sem), equal_var=False)

    sd_comb = np.sqrt(((n1 - 1) * np.var(com, ddof=1) + (n2 - 1) * np.var(sem, ddof=1)) / (n1 + n2 - 2))
    d = (np.mean(com) - np.mean(sem)) / sd_comb
    g = d * (1 - 3 / (4 * (n1 + n2) - 9))

    r_rb = 2 * mw.statistic / (n1 * n2) - 1
    hodges_lehmann = float(np.median(np.subtract.outer(com, sem)))

    return {
        "n_com_bot": n1,
        "n_sem_bot": n2,
        "media_com_bot": float(np.mean(com)),
        "media_sem_bot": float(np.mean(sem)),
        "mediana_com_bot": float(np.median(com)),
        "mediana_sem_bot": float(np.median(sem)),
        "welch_t": float(welch.statistic),
        "welch_gl": float(welch.df),
        "welch_p": float(welch.pvalue),
        "hedges_g": float(g),
        "diferenca_medias_h": float(np.mean(com) - np.mean(sem)),
        "mw_u": float(mw.statistic),
        "mw_p": float(mw.pvalue),
        "rank_biserial": float(r_rb),
        "hodges_lehmann_h": hodges_lehmann,
        "welch_log_t": float(welch_log.statistic),
        "welch_log_p": float(welch_log.pvalue),
        "razao_medianas": float(np.median(com) / np.median(sem)),
        "razao_medias_geometricas": float(np.exp(np.mean(np.log(com)) - np.mean(np.log(sem)))),
    }


def main():
    com, sem = carregar_reais()
    mediana, sigma = parametros_base(sem, com)
    print(f"Parâmetros base: mediana sem bot = {mediana:.2f} h, sigma combinado = {sigma:.2f}")

    tabela = rodar_simulacoes(mediana, sigma)
    tabela.to_csv(CAMINHO_SIMULACOES, index=False)

    reais = analisar_reais(com, sem)
    reais["mediana_base_simulacao"] = mediana
    reais["sigma_base_simulacao"] = sigma
    reais["repeticoes"] = REPETICOES
    reais["semente"] = SEMENTE
    poder_n = rodar_poder_por_n(mediana, sigma, reais["razao_medias_geometricas"])
    poder_n.to_csv(CAMINHO_PODER_N, index=False)

    with CAMINHO_REAIS.open("w", encoding="utf-8") as arquivo:
        json.dump(reais, arquivo, indent=2, ensure_ascii=False)

    tipo1 = tabela[(tabela["reducao_mediana"] == 0) & (tabela["alfa"] == 0.05)]
    print("\nErro tipo I (α = 0,05):")
    print(tipo1.pivot(index="situacao", columns="teste", values="taxa_rejeicao"))
    print("\nPoder (α = 0,05):")
    poder = tabela[tabela["alfa"] == 0.05].pivot_table(
        index=["situacao", "reducao_mediana"], columns="teste", values="taxa_rejeicao")
    print(poder)
    print("\nPoder por n (efeito observado):")
    print(poder_n.pivot(index="n", columns="teste", values="poder"))
    print("\nDados reais:")
    print(json.dumps(reais, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
