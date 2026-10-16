"""Casos de borda exigidos pelo enunciado (seção 7) para CFR (a) e recuperação."""

import pytest

from src.metricas import calculate_cfr_ci, calculate_recovery_time


def run(i, wf, conclusion, started, finished=None):
    return {"id": i, "workflow_id": wf, "conclusion": conclusion,
            "classification": {"success": "success", "failure": "failure"}.get(conclusion, "ignored"),
            "run_started_at": started, "updated_at": finished or started}


def test_exemplo_do_enunciado_recuperacao_de_1h20():
    runs = [
        run(1, 1, "success", "2026-03-01T09:00:00Z"),
        run(2, 1, "failure", "2026-03-01T10:00:00Z"),
        run(3, 1, "failure", "2026-03-01T10:30:00Z"),
        run(4, 1, "success", "2026-03-01T11:15:00Z", "2026-03-01T11:20:00Z"),
    ]
    result = calculate_recovery_time(runs)
    assert result["recovery_times_hours"] == [pytest.approx(80 / 60)]
    assert result["total_episodes"] == 1 and result["censored_episodes"] == 0


def test_falha_nunca_recuperada_e_censurada_e_nao_descartada():
    runs = [run(1, 1, "success", "2026-03-01T09:00:00Z"), run(2, 1, "failure", "2026-03-01T10:00:00Z")]
    result = calculate_recovery_time(runs)
    assert result["censored_episodes"] == 1 and result["censored_rate"] == 1.0
    assert result["median_hours"] is None and result["recovery_times_hours"] == []


def test_runs_cancelled_sao_ignoradas_no_cfr_e_na_recuperacao():
    runs = [
        run(1, 1, "success", "2026-03-01T09:00:00Z"),
        run(2, 1, "cancelled", "2026-03-01T10:00:00Z"),   # não abre episódio
        run(3, 1, "success", "2026-03-01T11:00:00Z"),
    ]
    assert calculate_recovery_time(runs)["total_episodes"] == 0
    assert calculate_cfr_ci(runs) == {"successes": 2, "failures": 0, "evaluated_runs": 2, "cfr": 0.0}


def test_recuperacao_e_calculada_dentro_de_cada_workflow():
    runs = [
        run(1, 1, "success", "2026-03-01T09:00:00Z"),
        run(2, 2, "success", "2026-03-01T09:00:00Z"),
        run(3, 1, "failure", "2026-03-01T10:00:00Z"),
        run(4, 2, "success", "2026-03-01T10:30:00Z"),   # sucesso de OUTRO workflow não recupera o 1
        run(5, 1, "success", "2026-03-01T12:00:00Z"),
    ]
    result = calculate_recovery_time(runs)
    assert result["recovery_times_hours"] == [2.0]


def test_primeira_run_com_falha_sem_sucesso_anterior_nao_e_episodio():
    runs = [run(1, 1, "failure", "2026-03-01T09:00:00Z"), run(2, 1, "success", "2026-03-01T10:00:00Z")]
    assert calculate_recovery_time(runs)["total_episodes"] == 0


def test_run_sem_run_started_at_usa_created_at():
    a = run(1, 1, "success", "2026-03-01T09:00:00Z")
    b = {"id": 2, "workflow_id": 1, "classification": "failure", "created_at": "2026-03-01T10:00:00Z",
         "run_started_at": None, "updated_at": "2026-03-01T10:05:00Z"}
    c = run(3, 1, "success", "2026-03-01T11:00:00Z")
    assert calculate_recovery_time([a, b, c])["recovery_times_hours"] == [pytest.approx(1.0)]


def test_cfr_sem_runs_avaliadas_e_none_e_quartis():
    assert calculate_cfr_ci([])["cfr"] is None
    assert calculate_cfr_ci([run(1, 1, "skipped", "2026-03-01T09:00:00Z")])["cfr"] is None
    runs = []
    for k, hours in enumerate([1, 2, 3, 4, 5]):  # 5 episódios de 1..5 h
        base = f"2026-03-0{k + 1}T"
        runs += [run(10 * k + 1, 1, "success", base + "01:00:00Z"),
                 run(10 * k + 2, 1, "failure", base + "02:00:00Z"),
                 run(10 * k + 3, 1, "success", base + f"{2 + hours:02d}:00:00Z")]
    result = calculate_recovery_time(runs)
    assert result["median_hours"] == 3 and (result["q1_hours"], result["q3_hours"]) == (2, 4)
