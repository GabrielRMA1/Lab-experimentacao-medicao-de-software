import json

import pytest

from src.metricas.lead_time import (
    compute_from_cache_dir,
    compute_release_lead_time,
    compute_repository_lead_time,
    intervals_from_cache,
    iqr_or_none,
    median_or_none,
    parse_iso,
    save_results,
)


def commit(sha, date):
    return {"sha": sha, "commit": {"author": {"date": date}}}


def interval(to_release, until, commits, since="2025-01-01T00:00:00Z"):
    return {
        "from_release": "anterior",
        "to_release": to_release,
        "since": since,
        "until": until,
        "commits": commits,
    }


@pytest.fixture
def exemplo_professor():
    """v1.1 publicada em 15/03 com commits de 02/03, 10/03 e 14/03."""
    return [
        interval(
            "v1.1",
            "2025-03-15T00:00:00Z",
            [
                commit("a", "2025-03-02T00:00:00Z"),
                commit("b", "2025-03-10T00:00:00Z"),
                commit("c", "2025-03-14T00:00:00Z"),
            ],
        )
    ]



def test_exemplo_professor_variante_a_13_dias(exemplo_professor):
    result = compute_repository_lead_time("o/r", exemplo_professor)
    assert result["lead_time_release_mediana_h"] == 13 * 24


def test_exemplo_professor_variante_b_13_5_1_dias(exemplo_professor):
    result = compute_release_lead_time(
        "2025-03-15T00:00:00Z", exemplo_professor[0]["commits"]
    )
    assert sorted(result["commit_lead_times_h"]) == [24, 5 * 24, 13 * 24]
    repo = compute_repository_lead_time("o/r", exemplo_professor)
    assert repo["lead_time_commit_mediana_h"] == 5 * 24 



def test_mediana_entre_releases_variante_a():
    intervals = [
        interval("v1", "2025-03-11T00:00:00Z", [commit("a", "2025-03-10T00:00:00Z")]),
        interval("v2", "2025-03-13T00:00:00Z", [commit("b", "2025-03-10T00:00:00Z")]),
        interval("v3", "2025-03-20T00:00:00Z", [commit("c", "2025-03-10T00:00:00Z")]),
    ]
    result = compute_repository_lead_time("o/r", intervals)
    assert result["n_releases_avaliadas"] == 3
    assert result["lead_time_release_mediana_h"] == 72


def test_commit_antigo_esquecido_explode_a_mas_pouco_afeta_b():
    """Pista do enunciado: variante (a) é sensível, (b) não."""
    commits = [commit("old", "2025-01-01T00:00:00Z")] + [
        commit(f"n{i}", "2025-03-14T00:00:00Z") for i in range(9)
    ]
    result = compute_repository_lead_time(
        "o/r", [interval("v1", "2025-03-15T00:00:00Z", commits)]
    )
    assert result["lead_time_release_mediana_h"] > 70 * 24
    assert result["lead_time_commit_mediana_h"] == 24



def test_release_sem_commits_nao_entra_e_e_contada():
    intervals = [
        interval("v1", "2025-03-15T00:00:00Z", []),
        interval("v2", "2025-03-20T00:00:00Z", [commit("a", "2025-03-19T00:00:00Z")]),
    ]
    result = compute_repository_lead_time("o/r", intervals)
    assert result["n_releases_sem_commits"] == 1
    assert result["n_releases_avaliadas"] == 1
    assert result["lead_time_release_mediana_h"] == 24


def test_repositorio_com_uma_unica_release_nao_tem_intervalos():
    result = compute_repository_lead_time("o/r", [])
    assert result["lead_time_release_mediana_h"] is None
    assert result["lead_time_commit_mediana_h"] is None
    assert result["n_releases_avaliadas"] == 0


def test_commit_sem_data_ou_posterior_a_release_e_invalido():
    commits = [
        commit("a", "2025-03-14T00:00:00Z"),
        commit("b", None),
        commit("c", "2025-03-16T00:00:00Z"),
    ]
    result = compute_release_lead_time("2025-03-15T00:00:00Z", commits)
    assert result["n_commits"] == 1
    assert result["n_invalidos"] == 2


def test_commit_duplicado_em_duas_releases_conta_uma_vez():
    intervals = [
        interval("v1", "2025-03-11T00:00:00Z", [commit("dup", "2025-03-10T00:00:00Z")]),
        interval("v2", "2025-03-13T00:00:00Z", [commit("dup", "2025-03-10T00:00:00Z")]),
    ]
    result = compute_repository_lead_time("o/r", intervals)
    assert result["n_commits"] == 1
    assert result["n_commits_duplicados"] == 1
    assert result["n_releases_sem_commits"] == 1


def test_release_sem_data_e_contada():
    result = compute_repository_lead_time(
        "o/r", [interval("v1", None, [commit("a", "2025-03-10T00:00:00Z")])]
    )
    assert result["n_releases_sem_data"] == 1
    assert result["lead_time_release_mediana_h"] is None


def test_janela_de_observacao_exclui_releases_fora():
    intervals = [
        interval("v1", "2024-01-01T00:00:00Z", [commit("a", "2023-12-31T00:00:00Z")]),
        interval("v2", "2025-03-15T00:00:00Z", [commit("b", "2025-03-14T00:00:00Z")]),
    ]
    result = compute_repository_lead_time(
        "o/r", intervals, "2025-01-01T00:00:00Z", "2025-12-31T23:59:59Z"
    )
    assert result["n_releases_fora_janela"] == 1
    assert result["n_releases_avaliadas"] == 1
    assert result["lead_time_release_mediana_h"] == 24


def test_commit_na_mesma_hora_da_release_tem_lead_time_zero():
    result = compute_release_lead_time(
        "2025-03-15T00:00:00Z", [commit("a", "2025-03-15T00:00:00Z")]
    )
    assert result["lead_time_release_h"] == 0



def test_parse_iso_aceita_z_e_rejeita_lixo():
    assert parse_iso("2025-03-15T00:00:00Z").tzinfo is not None
    assert parse_iso("2025-03-15T00:00:00").tzinfo is not None
    assert parse_iso("nao-e-data") is None
    assert parse_iso(None) is None


def test_median_e_iqr():
    assert median_or_none([]) is None
    assert median_or_none([1, 3, 2]) == 2
    assert iqr_or_none([1]) is None
    assert iqr_or_none([1, 2, 3, 4, 5]) == (2, 4)



def test_intervals_from_cache_le_chave_since_until():
    record = {
        "_pipeline_cache": {
            "commits_between_releases": {
                "2025-03-01T00:00:00Z|2025-03-15T00:00:00Z": {
                    "items": [commit("a", "2025-03-02T00:00:00Z")],
                    "complete": True,
                }
            }
        }
    }
    intervals = intervals_from_cache(record)
    assert intervals[0]["until"] == "2025-03-15T00:00:00Z"
    assert len(intervals[0]["commits"]) == 1
    assert intervals_from_cache({}) == []


def test_pipeline_cache_para_csv_reproduzivel(tmp_path):
    record = {
        "full_name": "o/r",
        "_pipeline_cache": {
            "commits_between_releases": {
                "2025-03-01T00:00:00Z|2025-03-15T00:00:00Z": {
                    "items": [commit("a", "2025-03-02T00:00:00Z")],
                    "complete": False,
                }
            }
        },
    }
    (tmp_path / "o__r.json").write_text(json.dumps(record), encoding="utf-8")
    (tmp_path / "vazio__repo.json").write_text("{}", encoding="utf-8")

    rows = compute_from_cache_dir(tmp_path)
    assert len(rows) == 2
    por_nome = {r["full_name"]: r for r in rows}
    assert por_nome["o/r"]["lead_time_release_mediana_h"] == 13 * 24
    assert por_nome["o/r"]["coleta_incompleta"] is True
    assert por_nome["vazio/repo"]["lead_time_release_mediana_h"] is None

    out = tmp_path / "saida"
    save_results(rows, out)
    assert (out / "lead_time.csv").exists()
    assert json.loads((out / "lead_time.json").read_text())[0]["full_name"]
    save_results([], tmp_path / "vazio")
