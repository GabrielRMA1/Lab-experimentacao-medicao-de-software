"""Pipeline reprodutível de mineração das métricas DORA (Lab 03).

Uso (a partir da pasta ``Lab 3``)::

    python -m src.pipeline search        # candidatos -> data/candidates.json
    python -m src.pipeline collect       # coleta com cache/retomada
    python -m src.pipeline consolidate   # funil + dataset + dicionário
"""
