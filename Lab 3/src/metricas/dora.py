"""Classificação DORA (tabela de referência da disciplina, RQ 07).

Cada métrica recebe um nível: 4 = Elite, 3 = High, 2 = Medium, 1 = Low.
A categoria geral é a **mediana** dos níveis, **arredondada para baixo**.

| Métrica                     | Elite     | High           | Medium              | Low        |
|-----------------------------|-----------|----------------|---------------------|------------|
| Deployment frequency (/sem) | >= 7      | >= 1 e < 7     | >= 1/mês e < 1/sem  | < 1/mês    |
| Lead time (mediana, horas)  | < 24      | 24 a < 168     | 168 a < 720         | >= 720     |
| CFR (proporção 0–1)         | <= 0,15   | > 0,15 e <= 0,30 | > 0,30 e <= 0,45  | > 0,45     |
| Recuperação (mediana, h)    | < 1       | 1 a < 24       | 24 a < 168          | >= 168     |

Regra do grupo para métrica ausente (não está no enunciado — documentada no
artigo): uma métrica sem valor (ex.: nenhum episódio de falha recuperado,
nenhuma release avaliável para o CFR) **fica de fora** da mediana. A
categoria geral exige pelo menos ``MIN_METRICAS`` (3) das 4 métricas; com
menos, o repositório é "não classificável" (``None``) e é contado à parte.

Módulo de cálculo puro (sem API).
"""

from __future__ import annotations

import math
import statistics
from typing import Any

ELITE, HIGH, MEDIUM, LOW = 4, 3, 2, 1
NOMES = {ELITE: "Elite", HIGH: "High", MEDIUM: "Medium", LOW: "Low"}
ORDEM = ["Elite", "High", "Medium", "Low"]

SEMANAS_POR_ANO = 365.25 / 7  # ~52,18
UMA_POR_MES_EM_SEMANAS = 12 / SEMANAS_POR_ANO  # 1 release/mês ~ 0,23/semana
HORAS_DIA, HORAS_SEMANA, HORAS_30_DIAS = 24.0, 168.0, 720.0
MIN_METRICAS = 3


def _valido(valor: Any) -> bool:
    if valor is None:
        return False
    try:
        return not math.isnan(float(valor))
    except (TypeError, ValueError):
        return False


def nivel_deploy_freq(por_semana: float | None) -> int | None:
    if not _valido(por_semana):
        return None
    if por_semana >= 7:
        return ELITE
    if por_semana >= 1:
        return HIGH
    if por_semana >= UMA_POR_MES_EM_SEMANAS:
        return MEDIUM
    return LOW


def nivel_lead_time(horas: float | None) -> int | None:
    if not _valido(horas):
        return None
    if horas < HORAS_DIA:
        return ELITE
    if horas < HORAS_SEMANA:
        return HIGH
    if horas < HORAS_30_DIAS:
        return MEDIUM
    return LOW


def nivel_cfr(proporcao: float | None) -> int | None:
    """``proporcao`` de 0 a 1 (0,15 = 15%)."""

    if not _valido(proporcao):
        return None
    if proporcao <= 0.15:
        return ELITE
    if proporcao <= 0.30:
        return HIGH
    if proporcao <= 0.45:
        return MEDIUM
    return LOW


def nivel_recuperacao(horas: float | None) -> int | None:
    if not _valido(horas):
        return None
    if horas < 1:
        return ELITE
    if horas < HORAS_DIA:
        return HIGH
    if horas < HORAS_SEMANA:
        return MEDIUM
    return LOW


def categoria_geral(niveis: list[int | None], minimo: int = MIN_METRICAS) -> int | None:
    """Mediana dos níveis disponíveis, arredondada para baixo.

    ``(4, 3, 3, 1)`` -> mediana 3 -> High. ``(4, 3, 2, 1)`` -> 2,5 -> Medium.
    """

    validos = [n for n in niveis if n is not None]
    if len(validos) < minimo:
        return None
    return math.floor(statistics.median(validos))


def classificar(
    deploy_freq: float | None,
    lead_time_h: float | None,
    cfr: float | None,
    recuperacao_h: float | None,
) -> dict[str, Any]:
    """Níveis por métrica + categoria geral (número e nome)."""

    niveis = {
        "nivel_df": nivel_deploy_freq(deploy_freq),
        "nivel_lt": nivel_lead_time(lead_time_h),
        "nivel_cfr": nivel_cfr(cfr),
        "nivel_rec": nivel_recuperacao(recuperacao_h),
    }
    geral = categoria_geral(list(niveis.values()))
    return {**niveis, "geral": geral, "categoria": NOMES.get(geral) if geral else None}
