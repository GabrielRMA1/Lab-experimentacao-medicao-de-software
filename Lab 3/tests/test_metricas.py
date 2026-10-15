import pytest

from src.metricas import calculate_cfr_ci, calculate_recovery_time


def run(
    run_id,
    workflow_id,
    classification,
    started,
    updated=None,
):
    return {
        "id": run_id,
        "workflow_id": workflow_id,
        "classification": classification,
        "run_started_at": started,
        "updated_at": updated or started,
    }


def test_cfr_counts_only_success_and_failure():
    result = calculate_cfr_ci(
        [
            run(1, 10, "success", "2026-01-01T10:00:00Z"),
            run(2, 10, "failure", "2026-01-01T11:00:00Z"),
            run(3, 10, "ignored", "2026-01-01T12:00:00Z"),
        ]
    )

    assert result["successes"] == 1
    assert result["failures"] == 1
    assert result["evaluated_runs"] == 2
    assert result["cfr"] == pytest.approx(0.5)


def test_cfr_accepts_conclusion_when_classification_is_absent():
    result = calculate_cfr_ci(
        [
            {"conclusion": "success"},
            {"conclusion": "timed_out"},
            {"conclusion": "cancelled"},
        ]
    )

    assert result["evaluated_runs"] == 2
    assert result["cfr"] == pytest.approx(0.5)


def test_cfr_without_evaluable_runs_is_none():
    result = calculate_cfr_ci(
        [{"classification": "ignored"}]
    )

    assert result["evaluated_runs"] == 0
    assert result["cfr"] is None


def test_recovery_uses_next_success_of_same_workflow():
    result = calculate_recovery_time(
        [
            run(1, 10, "success", "2026-01-01T09:00:00Z"),
            run(2, 10, "failure", "2026-01-01T10:00:00Z"),
            run(3, 10, "failure", "2026-01-01T10:30:00Z"),
            run(4, 10, "success", "2026-01-01T11:00:00Z", "2026-01-01T11:20:00Z"),
        ]
    )

    assert result["total_episodes"] == 1
    assert result["recovered_episodes"] == 1
    assert result["censored_episodes"] == 0
    assert result["median_hours"] == pytest.approx(1 + 20 / 60)


def test_recovery_keeps_workflows_separate():
    result = calculate_recovery_time(
        [
            run(1, 10, "success", "2026-01-01T09:00:00Z"),
            run(2, 10, "failure", "2026-01-01T10:00:00Z"),
            run(3, 20, "success", "2026-01-01T10:10:00Z"),
            run(4, 20, "failure", "2026-01-01T10:20:00Z"),
            run(5, 10, "success", "2026-01-01T11:00:00Z", "2026-01-01T11:10:00Z"),
            run(6, 20, "success", "2026-01-01T11:20:00Z", "2026-01-01T11:30:00Z"),
        ]
    )

    assert result["total_episodes"] == 2
    assert sorted(result["recovery_times_hours"]) == pytest.approx([1.1666666667, 1.1666666667])


def test_recovery_marks_unrecovered_episode_as_censored():
    result = calculate_recovery_time(
        [
            run(1, 10, "success", "2026-01-01T09:00:00Z"),
            run(2, 10, "failure", "2026-01-01T10:00:00Z"),
        ]
    )

    assert result["recovered_episodes"] == 0
    assert result["censored_episodes"] == 1
    assert result["censored_rate"] == pytest.approx(1.0)
    assert result["median_hours"] is None


def test_recovery_ignores_cancelled_and_skipped_runs():
    result = calculate_recovery_time(
        [
            run(1, 10, "success", "2026-01-01T09:00:00Z"),
            run(2, 10, "ignored", "2026-01-01T09:30:00Z"),
            run(3, 10, "failure", "2026-01-01T10:00:00Z"),
            run(4, 10, "ignored", "2026-01-01T10:30:00Z"),
            run(5, 10, "success", "2026-01-01T11:00:00Z", "2026-01-01T11:15:00Z"),
        ]
    )

    assert result["recovered_episodes"] == 1
    assert result["median_hours"] == pytest.approx(1.25)


def test_recovery_requires_workflow_identity():
    with pytest.raises(ValueError, match="workflow_id"):
        calculate_recovery_time(
            [
                {
                    "classification": "failure",
                    "run_started_at": "2026-01-01T10:00:00Z",
                    "updated_at": "2026-01-01T10:05:00Z",
                }
            ]
        )
