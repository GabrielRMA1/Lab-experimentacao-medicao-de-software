"""Métricas DORA (cálculo puro, sem chamadas à API do GitHub).

* ``ci``            — CFR (a) e tempo de recuperação (RQ 03a, RQ 04).
* ``lead_time``     — Lead time for changes (RQ 02).
* ``heuristica``    — heurística de release corretiva (RQ 03b).
* ``cfr_release``   — CFR (b) e rework rate (RQ 03b, RQ 08).
"""

from .ci import calculate_cfr_ci, calculate_recovery_time

__all__ = ["calculate_cfr_ci", "calculate_recovery_time"]
