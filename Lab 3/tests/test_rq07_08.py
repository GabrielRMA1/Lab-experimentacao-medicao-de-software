"""RQ 07 (sensibilidade), RQ 08 (rework rate) e a análise completa."""

import pandas as pd
import pytest

from src.analise import executar_tudo, rq07, rq08
from tests.dados_sinteticos import dataset_sintetico, preparar_ambiente


def test_rq07_combinacao_identica_tem_kappa_1_e_zero_mudancas():
    df = dataset_sintetico()
    df["lt_commit_mediana_h"] = df["lt_release_mediana_h"]  # C3 == C1
    classes = rq07.classificar_combinacoes(df)
    par = {p["par"]: p for p in rq07.comparar_pares(classes)}["C1 × C3"]
    assert par["mudaram"] == 0 and par["kappa"] == pytest.approx(1.0)


def test_rq07_pre_release_aumenta_frequencia():
    df = dataset_sintetico()
    assert (rq07.frequencia(df, "release+pre") >= df["deploy_freq_semana"] - 1e-9).all()


def test_rq08_rework_rate(tmp_path):
    csv, saida, _ = preparar_ambiente(tmp_path)
    r = rq08.executar(pd.read_csv(csv), saida)
    assert r["n"] == 79 and "rho" in r
    assert (saida / "tab_rq08.tex").exists()


def test_executar_tudo_gera_tabelas_figuras_resumo_e_json(tmp_path):
    csv, saida, validacao = preparar_ambiente(tmp_path)
    resumo = executar_tudo(csv, saida, validacao)
    texto = resumo.read_text(encoding="utf-8")
    assert "RQ 05" in texto and "RQ 07" in texto
    for nome in ("tab_rq01_04", "tab_rq05", "tab_rq06", "tab_rq07_distribuicao",
                 "tab_rq07_pares", "tab_rq08"):
        assert (saida / f"{nome}.tex").exists()
    for fig in ("rq01_04_distribuicoes", "rq05_dispersao", "rq06_efeitos", "rq07_radar"):
        assert (saida / "figuras" / f"{fig}.png").exists()
    assert (saida / "resultados.json").exists()
