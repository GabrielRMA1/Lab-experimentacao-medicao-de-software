import pytest

from src.metricas.lead_time import make_compare_key
from src.validacao.avaliar_heuristica import (
    evaluate_versions,
    score_predictions,
    write_results,
)


def test_exemplo_do_enunciado_precisao_recall_f1():
    # heurística marcou 40; 30 corretas. Consenso tem 50 corretivas no total.
    y_true = [1] * 30 + [0] * 10 + [1] * 20 + [0] * 40
    y_pred = [1] * 30 + [1] * 10 + [0] * 20 + [0] * 40
    s = score_predictions(y_true, y_pred)
    assert s["precisao"] == pytest.approx(0.75)
    assert s["recall"] == pytest.approx(0.60)
    assert s["f1"] == pytest.approx(2 * 0.75 * 0.6 / (0.75 + 0.6))  # ≈ 0,667
    assert (s["vp"], s["fp"], s["fn"], s["vn"]) == (30, 10, 20, 40)


def test_sem_nenhuma_predicao_positiva_nao_divide_por_zero():
    s = score_predictions([1, 0, 1], [0, 0, 0])
    assert s["precisao"] == 0.0 and s["recall"] == 0.0 and s["f1"] == 0.0


def make_record():
    rel = lambda tag, day: {"tag_name": tag, "published_at": f"2026-03-{day:02d}T00:00:00Z",
                            "prerelease": False, "draft": False, "id": day}
    items = lambda *m: {"complete": True, "items": [{"sha": str(i), "message": x} for i, x in enumerate(m)]}
    return {"full_name": "o/r", "_pipeline_cache": {
        "releases_v2": {"complete": True, "items": [rel("v1.0.0", 1), rel("v1.0.1", 5), rel("v1.1.0", 9)]},
        "compare_v1": {
            make_compare_key("a", "b", "v1.0.0", "v1.0.1"): items("fix: crash"),
            make_compare_key("a", "b", "v1.0.1", "v1.1.0"): items("feat: nova tela"),
        }}}


def test_evaluate_versions_compara_com_o_consenso():
    consensus = [
        {"full_name": "o/r", "tag_name": "v1.0.1", "corretiva": "sim"},
        {"full_name": "o/r", "tag_name": "v1.1.0", "corretiva": "nao"},
        {"full_name": "o/r", "tag_name": "v1.0.0", "corretiva": ""},   # sem rótulo: pulada
    ]
    results = evaluate_versions(consensus, lambda name: make_record())
    by_version = {r["versao"]: r for r in results}
    assert by_version["v3_patch_ou_palavras"]["f1"] == 1.0
    assert by_version["v1_patch"]["n"] == 2


def test_write_results_escolhe_melhor_f1(tmp_path):
    results = [{"versao": "a", "precisao": .5, "recall": .5, "f1": .5, "n": 4, "vp": 1, "fp": 1, "fn": 1, "vn": 1},
               {"versao": "b", "precisao": .9, "recall": .8, "f1": .85, "n": 4, "vp": 1, "fp": 1, "fn": 1, "vn": 1}]
    chosen = write_results(results, tmp_path)
    assert chosen["versao"] == "b" and chosen["atinge_meta_f1_0_70"] is True
    assert (tmp_path / "heuristica_versoes.csv").exists()
    assert (tmp_path / "heuristica_escolhida.json").exists()
