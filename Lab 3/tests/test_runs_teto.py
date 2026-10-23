"""Teto de 1.000 runs por consulta: subdivisão do intervalo e registro de truncamento."""

from __future__ import annotations

import pytest

from src.collectors import repositories as repo_mod
from src.collectors.repositories import (
    GitHubClient,
    collect_repository_workflow_runs,
    load_cached_repository,
)
from src.pipeline.config import Config
from src.pipeline.dataset import build_row

REPO = {
    "full_name": "example/busy",
    "owner": "example",
    "name": "busy",
    "default_branch": "main",
}


class Resp:
    def __init__(self, data):
        self._data, self.status_code, self.headers, self.text = data, 200, {}, ""

    def json(self):
        return self._data


def run(run_id: int, created: str) -> dict:
    return {
        "id": run_id, "workflow_id": 1, "name": "CI", "head_sha": f"s{run_id}",
        "head_branch": "main", "event": "push", "status": "completed",
        "conclusion": "success", "created_at": created,
        "updated_at": created, "run_started_at": created,
    }


def in_range(created: str, rng: str) -> bool:
    low, _, high = rng.partition("..")
    if "T" not in low:  # intervalo por data (inclusivo)
        return low <= created[:10] <= high
    return low <= created <= high


class CappedClient(GitHubClient):
    """Devolve no máximo ``cap`` runs por consulta, como a API real."""

    def __init__(self, runs, cap):
        super().__init__(token="fake")
        self.runs, self.cap, self.ranges = runs, cap, []

    def get(self, path, params=None):
        rng = (params or {})["created"]
        self.ranges.append(rng)
        hits = [r for r in self.runs if in_range(r["created_at"], rng)]
        return Resp({"total_count": len(hits), "workflow_runs": hits[: self.cap]})


@pytest.fixture
def cache(monkeypatch, tmp_path):
    monkeypatch.setattr(repo_mod, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(repo_mod, "RUNS_QUERY_CAP", 4)
    return tmp_path


def test_mes_abaixo_do_teto_nao_subdivide(cache):
    runs = [run(i, f"2026-01-{10 + i:02d}T10:00:00Z") for i in range(3)]
    client = CappedClient(runs, cap=4)
    got = collect_repository_workflow_runs(
        client, REPO, "2026-01-01T00:00:00Z", "2026-01-31T23:59:59Z")
    assert client.ranges == ["2026-01-01..2026-01-31"]
    assert sorted(r["id"] for r in got) == [0, 1, 2]


def test_mes_no_teto_e_subdividido_ate_caber(cache):
    # 8 runs no mês, teto 4: o mês é dividido e nenhum run se perde
    runs = [run(i, f"2026-01-{2 + 3 * i:02d}T10:00:00Z") for i in range(8)]
    client = CappedClient(runs, cap=4)
    got = collect_repository_workflow_runs(
        client, REPO, "2026-01-01T00:00:00Z", "2026-01-31T23:59:59Z")
    assert len(client.ranges) > 1
    assert all("T" in r for r in client.ranges[1:])  # sub-intervalos com hora
    assert sorted(r["id"] for r in got) == list(range(8))  # sem duplicatas
    record = load_cached_repository("example/busy")
    assert not record["_pipeline_cache"].get("runs_truncados_v1")


def test_intervalo_que_nao_cabe_nem_em_1h_e_registrado(cache):
    # 6 runs no mesmo minuto: impossível caber em 4 -> truncado e registrado
    runs = [run(i, "2026-01-15T10:00:00Z") for i in range(6)]
    client = CappedClient(runs, cap=4)
    collect_repository_workflow_runs(
        client, REPO, "2026-01-01T00:00:00Z", "2026-01-31T23:59:59Z")
    record = load_cached_repository("example/busy")
    truncated = record["_pipeline_cache"]["runs_truncados_v1"]
    assert len(truncated) == 1 and "2026-01-15" in truncated[0]

    cfg = Config(observation_start="2026-01-01T00:00:00Z",
                 observation_end="2026-01-31T23:59:59Z")
    row = build_row(record, cfg, "v1_patch")
    assert row["runs_intervalos_truncados"] == 1


def test_retomada_nao_repete_chamadas(cache):
    runs = [run(i, f"2026-01-{2 + 3 * i:02d}T10:00:00Z") for i in range(8)]
    first = CappedClient(runs, cap=4)
    collect_repository_workflow_runs(
        first, REPO, "2026-01-01T00:00:00Z", "2026-01-31T23:59:59Z")
    again = CappedClient(runs, cap=4)
    got = collect_repository_workflow_runs(
        again, REPO, "2026-01-01T00:00:00Z", "2026-01-31T23:59:59Z")
    assert again.ranges == []  # tudo veio do cache
    assert len(got) == 8
