"""RQ 05 (Spearman) e RQ 06 (testes por fator, Holm e tamanho de efeito)."""

import pandas as pd
import pytest

from src.analise import rq05, rq06
from tests.dados_sinteticos import preparar_ambiente


def test_rq05_correlacao_perfeita_e_interpretacao():
    df = pd.DataFrame({"deploy_freq_semana": [1, 2, 3, 4, 5],
                       "cfr_ci": [0.1, 0.2, 0.3, 0.4, 0.5],
                       "cfr_entrega": [0.5, 0.4, 0.3, 0.2, 0.1]})
    r = rq05.correlacoes(df)
    assert r[0]["rho"] == pytest.approx(1.0) and r[1]["rho"] == pytest.approx(-1.0)
    assert rq05.interpretar_rho(-0.6) == "forte negativa"


def test_rq05_gera_tabela_e_dispersao(tmp_path):
    csv, saida, _ = preparar_ambiente(tmp_path)
    rq05.executar(pd.read_csv(csv), saida)
    assert (saida / "tab_rq05.tex").exists()
    assert (saida / "figuras" / "rq05_dispersao.png").exists()


def test_rq06_holm_tamanho_de_efeito_e_tipo_do_projeto(tmp_path):
    csv, saida, validacao = preparar_ambiente(tmp_path)
    testes = rq06.executar(pd.read_csv(csv), saida, validacao)
    fatores = {t["fator"] for t in testes}
    assert {"Linguagem", "Estrelas (quartis)", "Contribuidores (quartis)",
            "Tipo do projeto (amostra-ouro)"} <= fatores
    assert all(t["p_holm"] >= t["p"] for t in testes)
    assert (saida / "figuras" / "rq06_efeitos.png").exists()


def test_mann_whitney_e_cliff_delta_com_dois_grupos():
    valores = pd.Series([1, 2, 3, 4, 5, 6, 10, 11, 12, 13, 14, 15])
    grupos = pd.Series(["a"] * 6 + ["b"] * 6)
    r = rq06.testar(valores, grupos)
    assert r["teste"] == "Mann-Whitney"
    assert r["efeito"] == "δ = -1,000" and r["magnitude"] == "grande"


def test_grupo_pequeno_fica_fora_do_teste():
    valores = pd.Series(range(12))
    grupos = pd.Series(["a"] * 6 + ["b"] * 4 + ["c"] * 2)
    assert rq06.testar(valores, grupos) is None  # só "a" tem >= 5
