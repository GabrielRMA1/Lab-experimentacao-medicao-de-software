"""Cache segmentado: runs e compare em arquivos por intervalo (desempenho)."""

from __future__ import annotations

import json
import threading

from src.collectors import repositories as repo_mod
from src.collectors.repositories import (
    cache_path,
    load_cached_repository,
    load_segment,
    parts_dir,
    save_cached_repository,
    set_pipeline_value,
)
from src.pipeline.config import Config
from src.pipeline.merge import merge_caches
from src.pipeline.selecao import collect


def test_grupos_grandes_ficam_fora_do_arquivo_principal(monkeypatch, tmp_path):
    monkeypatch.setattr(repo_mod, "CACHE_DIR", tmp_path)
    record = {
        "full_name": "o/r", "stars": 5,
        "_pipeline_cache": {
            "releases_v2": {"items": [{"tag_name": "v1"}], "complete": True},
            "workflow_runs_monthly_v1": {"2026-01-01..2026-01-31": {"items": [{"id": 1}], "complete": True}},
            "compare_v1": {"a|b|v1...v2": {"items": [], "complete": True, "not_found": True}},
        },
    }
    save_cached_repository(record)

    main = json.loads(cache_path("o/r").read_text(encoding="utf-8"))
    assert set(main["_pipeline_cache"]) == {"releases_v2"}
    assert len(list(parts_dir("o/r").rglob("*.json"))) == 2
    assert load_cached_repository("o/r") == record  # remontado igual
    assert "workflow_runs_monthly_v1" not in load_cached_repository(
        "o/r", include_segments=False)["_pipeline_cache"]

    # gravar um valor simples não reescreve os intervalos
    set_pipeline_value("o/r", "decision", {"status": "accepted"})
    assert load_cached_repository("o/r")["_pipeline_cache"]["compare_v1"]


def test_cache_no_formato_antigo_e_migrado(monkeypatch, tmp_path):
    monkeypatch.setattr(repo_mod, "CACHE_DIR", tmp_path)
    legacy = {
        "full_name": "o/velho",
        "_pipeline_cache": {
            "decision": {"status": "accepted"},
            "workflow_runs_monthly_v1": {
                "2026-02-01..2026-02-28": {"items": [{"id": 9}], "next_url": "u", "complete": False}
            },
        },
    }
    cache_path("o/velho").write_text(json.dumps(legacy), encoding="utf-8")

    state = load_segment("o/velho", "workflow_runs_monthly_v1", "2026-02-01..2026-02-28")
    assert state == {"items": [{"id": 9}], "next_url": "u", "complete": False}
    main = json.loads(cache_path("o/velho").read_text(encoding="utf-8"))
    assert "workflow_runs_monthly_v1" not in main["_pipeline_cache"]
    assert main["_pipeline_cache"]["decision"] == {"status": "accepted"}


def test_merge_copia_a_pasta_de_intervalos(monkeypatch, tmp_path):
    source, dest = tmp_path / "outra", tmp_path / "dest"
    monkeypatch.setattr(repo_mod, "CACHE_DIR", source)
    save_cached_repository({
        "full_name": "o/r",
        "_pipeline_cache": {
            "decision": {"status": "accepted"},
            "compare_v1": {"k": {"items": [{"sha": "x"}], "complete": True}},
        },
    })
    merge_caches([source], dest)
    monkeypatch.setattr(repo_mod, "CACHE_DIR", dest)
    assert load_cached_repository("o/r")["_pipeline_cache"]["compare_v1"]["k"]["items"] == [{"sha": "x"}]


def test_repositorio_lento_nao_segura_os_demais():
    release = threading.Event()
    order: list[str] = []

    def evaluate(client, candidate, cfg):
        if candidate["full_name"] == "gigante/lento":
            release.wait(timeout=5)
        return {"status": "discarded", "reason": "x"}

    def log(message):
        order.append(message.split("] ")[-1].split(":")[0])
        if order.count("pequeno/c") == 1:
            release.set()

    candidates = [{"full_name": "gigante/lento", "stargazers_count": 100}] + [
        {"full_name": f"pequeno/{c}", "stargazers_count": 10} for c in "abc"
    ]
    cfg = Config(workers=2, sample_target=10)
    stats = collect(None, candidates, cfg, evaluate=evaluate, log=log)

    assert stats["evaluated"] == 4
    assert order.index("pequeno/c") < order.index("gigante/lento")
