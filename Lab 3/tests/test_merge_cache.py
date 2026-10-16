import json

import src.collectors.repositories as repositories
from src.pipeline.__main__ import main
from src.pipeline.merge import merge_caches


def write(directory, name, record):
    directory.mkdir(parents=True, exist_ok=True)
    (directory / name).write_text(json.dumps(record), encoding="utf-8")


def test_prefere_copia_com_decisao_e_nao_sobrescreve_melhor(tmp_path):
    a, b, dest = tmp_path / "a", tmp_path / "b", tmp_path / "dest"
    stub = {"full_name": "o/x", "stars": 1}                       # cache da S01: só metadados
    done = {"full_name": "o/x", "_pipeline_cache": {"decision": {"status": "accepted"}, "releases_v2": {}}}
    write(a, "o__x.json", stub)
    write(a, "o__so_em_a.json", {"full_name": "o/so_em_a"})
    write(b, "o__x.json", done)
    write(b, "_candidates.json", {"x": 1})                         # auxiliar: ignorado
    (b / "quebrado.json").write_text("{nao e json", encoding="utf-8")

    stats = merge_caches([a, b], dest)
    assert json.loads((dest / "o__x.json").read_text())["_pipeline_cache"]["decision"]
    assert (dest / "o__so_em_a.json").exists() and not (dest / "_candidates.json").exists()
    assert stats["invalid"] == 1

    again = merge_caches([a], dest)                                # fonte pior não sobrescreve
    assert json.loads((dest / "o__x.json").read_text())["_pipeline_cache"]["decision"]
    assert again["kept"] >= 1


def test_comando_merge_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(repositories, "CACHE_DIR", tmp_path / "cache")
    write(tmp_path / "outra", "o__y.json", {"full_name": "o/y"})
    assert main(["merge-cache", str(tmp_path / "outra")]) == 0
    assert (tmp_path / "cache" / "o__y.json").exists()
