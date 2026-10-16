"""Lead time (RQ 02) alimentado pelo cache ``compare_v1`` (S02)."""

from src.metricas.lead_time import (
    compute_repository_lead_time,
    intervals_from_cache,
    make_compare_key,
    parse_compare_key,
)

H = 24.0  # horas por dia


def c(sha, date, message="x"):
    return {"sha": sha, "message": message, "commit": {"author": {"date": date}}}


def test_exemplo_do_enunciado_via_compare():
    # v1.1 publicada em 15/03, com commits de 02/03, 10/03 e 14/03
    key = make_compare_key("2026-02-01T00:00:00Z", "2026-03-15T00:00:00Z", "v1.0", "v1.1")
    record = {"_pipeline_cache": {"compare_v1": {key: {"complete": True, "items": [
        c("a", "2026-03-02T00:00:00Z"), c("b", "2026-03-10T00:00:00Z"),
        c("c", "2026-03-14T00:00:00Z")]}}}}
    result = compute_repository_lead_time("o/r", intervals_from_cache(record))
    assert result["lead_time_release_mediana_h"] == 13 * H          # (a)
    assert result["lead_time_commit_mediana_h"] == 5 * H            # (b): 13, 5, 1 dias
    assert result["n_releases_compare_404"] == 0


def test_commit_antigo_esquecido_explode_a_variante_a_mas_pouco_a_b():
    """Dica do enunciado: um commit antigo infla (a) e quase não mexe em (b)."""
    base = [c(f"n{i}", f"2026-03-{10 + i}T00:00:00Z") for i in range(5)]
    old = c("old", "2025-06-01T00:00:00Z")  # escrito ANTES da release anterior
    key = make_compare_key("2026-03-01T00:00:00Z", "2026-03-20T00:00:00Z", "v1", "v2")
    record = {"_pipeline_cache": {"compare_v1": {key: {"complete": True, "items": base + [old]}}}}
    result = compute_repository_lead_time("o/r", intervals_from_cache(record))
    assert result["lead_time_release_mediana_h"] > 200 * H
    assert result["lead_time_commit_mediana_h"] < 10 * H


def test_compare_404_e_contado_e_ignorado():
    k1 = make_compare_key("2026-01-01T00:00:00Z", "2026-02-01T00:00:00Z", "v1", "v2")
    k2 = make_compare_key("2026-02-01T00:00:00Z", "2026-03-01T00:00:00Z", "v2", "v3")
    record = {"_pipeline_cache": {"compare_v1": {
        k1: {"complete": True, "items": [c("a", "2026-01-31T00:00:00Z")]},
        k2: {"complete": True, "items": [], "not_found": True}}}}
    result = compute_repository_lead_time("o/r", intervals_from_cache(record))
    assert result["n_releases_compare_404"] == 1
    assert result["n_releases_avaliadas"] == 1
    assert result["n_releases_sem_commits"] == 0


def test_chave_roundtrip_e_chave_legada_da_s01():
    key = make_compare_key("2026-01-01T00:00:00Z", "2026-02-01T00:00:00Z", "v1.0.0", "v1.1.0")
    assert parse_compare_key(key) == {
        "since": "2026-01-01T00:00:00Z", "until": "2026-02-01T00:00:00Z",
        "from_release": "v1.0.0", "to_release": "v1.1.0"}
    legacy = parse_compare_key("2026-01-01T00:00:00Z|2026-02-01T00:00:00Z")
    assert legacy["until"] == "2026-02-01T00:00:00Z" and legacy["to_release"] is None


def test_cache_legado_da_s01_ainda_funciona_como_fallback():
    record = {"_pipeline_cache": {"commits_between_releases": {
        "2026-01-01T00:00:00Z|2026-01-15T00:00:00Z": {
            "complete": True, "items": [c("a", "2026-01-14T00:00:00Z")]}}}}
    intervals = intervals_from_cache(record)
    assert intervals[0]["until"] == "2026-01-15T00:00:00Z"
    assert compute_repository_lead_time("o/r", intervals)["lead_time_release_mediana_h"] == 24
