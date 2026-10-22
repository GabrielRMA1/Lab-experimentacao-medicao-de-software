"""RQ 01–04: estatística descritiva, classificação C1 e violinos."""

import pandas as pd

from src.analise import rq01_04
from src.analise.comum import descrever, fmt, fmt_p, salvar_tabela, semanas_da_janela
from tests.dados_sinteticos import dataset_sintetico, preparar_ambiente


def test_rq01_04_gera_tabelas_classificacao_e_figura(tmp_path):
    csv, saida, _ = preparar_ambiente(tmp_path)
    resumo = rq01_04.executar(pd.read_csv(csv), saida)
    for nome in ("tab_rq01_04", "tab_censura", "tab_dora_c1"):
        assert (saida / f"{nome}.tex").exists() and (saida / f"{nome}.csv").exists()
    assert (saida / "figuras" / "rq01_04_distribuicoes.png").exists()
    assert (saida / "classificacao_c1.csv").exists()
    assert resumo["Deployment frequency"]["n"] == 80
    assert sum(resumo["categorias_c1"].values()) + resumo["nao_classificaveis_c1"] == 80


def test_tabela_latex_escapa_caracteres(tmp_path):
    salvar_tabela([{"Métrica": "CFR_a", "Valor": "10%", "Efeito": "ε² = 0,1"}], tmp_path, "t", "x")
    tex = (tmp_path / "t.tex").read_text(encoding="utf-8")
    assert r"CFR\_a" in tex and r"10\%" in tex and r"$\varepsilon^2$" in tex


def test_formatacao_brasileira_e_semanas():
    assert fmt(1234.5, 1) == "1.234,5" and fmt(None) == "--" and fmt(3) == "3"
    assert fmt_p(0.0001) == "< 0,001"
    assert descrever([])["n"] == 0
    assert abs(semanas_da_janela(dataset_sintetico()) - 365.25 / 7) < 1e-6
