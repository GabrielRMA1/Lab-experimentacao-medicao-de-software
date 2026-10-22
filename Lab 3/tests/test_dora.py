"""Classificação DORA: cortes da tabela de referência e categoria geral."""

import math

import pytest

from src.metricas.dora import (
    ELITE, HIGH, LOW, MEDIUM, UMA_POR_MES_EM_SEMANAS,
    categoria_geral, classificar, nivel_cfr, nivel_deploy_freq,
    nivel_lead_time, nivel_recuperacao,
)


@pytest.mark.parametrize("valor, esperado", [
    (7, ELITE), (10, ELITE), (6.99, HIGH), (1, HIGH),
    (0.99, MEDIUM), (UMA_POR_MES_EM_SEMANAS, MEDIUM),
    (UMA_POR_MES_EM_SEMANAS - 0.01, LOW), (0, LOW),
])
def test_deploy_frequency(valor, esperado):
    assert nivel_deploy_freq(valor) == esperado


@pytest.mark.parametrize("horas, esperado", [
    (0, ELITE), (23.9, ELITE), (24, HIGH), (167.9, HIGH),
    (168, MEDIUM), (719.9, MEDIUM), (720, LOW), (5000, LOW),
])
def test_lead_time(horas, esperado):
    assert nivel_lead_time(horas) == esperado


@pytest.mark.parametrize("cfr, esperado", [
    (0, ELITE), (0.15, ELITE), (0.1501, HIGH), (0.30, HIGH),
    (0.31, MEDIUM), (0.45, MEDIUM), (0.4501, LOW), (1, LOW),
])
def test_cfr(cfr, esperado):
    assert nivel_cfr(cfr) == esperado


@pytest.mark.parametrize("horas, esperado", [
    (0.5, ELITE), (1, HIGH), (23.9, HIGH), (24, MEDIUM),
    (167.9, MEDIUM), (168, LOW),
])
def test_recuperacao(horas, esperado):
    assert nivel_recuperacao(horas) == esperado


@pytest.mark.parametrize("func", [
    nivel_deploy_freq, nivel_lead_time, nivel_cfr, nivel_recuperacao,
])
def test_valor_ausente_nao_tem_nivel(func):
    assert func(None) is None
    assert func(math.nan) is None
    assert func("abc") is None


def test_exemplo_do_enunciado_4_3_3_1_e_high():
    assert categoria_geral([4, 3, 3, 1]) == HIGH


def test_mediana_fracionaria_arredonda_para_baixo():
    assert categoria_geral([4, 3, 2, 1]) == MEDIUM   # 2,5 -> 2
    assert categoria_geral([4, 4, 3, 3]) == HIGH     # 3,5 -> 3


def test_metrica_ausente_fica_fora_da_mediana():
    assert categoria_geral([4, 4, None, 1]) == ELITE  # mediana de (4, 4, 1)
    assert categoria_geral([4, None, None, 1]) is None  # menos de 3 métricas


def test_classificar_repositorio_completo():
    resultado = classificar(
        deploy_freq=2.0,        # High
        lead_time_h=12,         # Elite
        cfr=0.40,               # Medium
        recuperacao_h=200,      # Low
    )
    assert resultado == {
        "nivel_df": HIGH, "nivel_lt": ELITE, "nivel_cfr": MEDIUM,
        "nivel_rec": LOW, "geral": MEDIUM, "categoria": "Medium",
    }


def test_classificar_sem_episodios_de_falha():
    resultado = classificar(8, 10, 0.05, None)
    assert resultado["nivel_rec"] is None
    assert resultado["categoria"] == "Elite"


def test_classificar_nao_classificavel():
    assert classificar(None, None, 0.1, None)["categoria"] is None
