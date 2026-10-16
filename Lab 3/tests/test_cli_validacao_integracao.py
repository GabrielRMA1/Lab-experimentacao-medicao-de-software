"""CLI de ponta a ponta: collect -> consolidate -> amostra-ouro -> rótulos ->
concordancia -> heuristica.

ATENÇÃO: os rótulos dos 3 'avaliadores' aqui são SINTÉTICOS (gerados pelo
teste para exercitar o fluxo). Os rótulos reais são manuais e independentes.
"""

import csv
import json

import pytest

import src.collectors.repositories as repositories
from src.pipeline.__main__ import main
from src.pipeline.selecao import save_candidates
from tests.fake_github import FakeGitHub, candidate, good_repo


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(repositories, "CACHE_DIR", tmp_path / "cache")
    (tmp_path / "cache").mkdir()
    monkeypatch.setenv("LAB3_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("LAB3_DOCS_DIR", str(tmp_path / "docs"))
    monkeypatch.setenv("OBSERVATION_START", "2026-01-01T00:00:00Z")
    monkeypatch.setenv("OBSERVATION_END", "2026-06-30T23:59:59Z")
    monkeypatch.setenv("SAMPLE_TARGET", "100")
    monkeypatch.setenv("MIN_SAMPLE", "70")
    monkeypatch.setenv("WORKERS", "2")
    world = {f"o/r{i:02d}": good_repo() for i in range(70)}
    fake = FakeGitHub(world)
    monkeypatch.setattr(repositories, "GitHubClient", lambda *a, **k: fake)
    save_candidates(tmp_path / "data" / "candidates.json",
                    [candidate(n, 5000 - i) for i, n in enumerate(world)], "stars:>1000")
    return tmp_path


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_fluxo_completo(env, capsys):
    data = env / "data"
    assert main(["collect", "--shard", "1/1"]) == 0
    assert main(["consolidate"]) == 0
    dataset = read_csv(data / "dataset" / "dataset_repos.csv")
    assert len(dataset) == 70
    assert (env / "docs" / "DICIONARIO_DADOS.md").exists()
    assert json.loads((data / "funil.json").read_text())["atinge_minimo"] is True

    # --- amostra-ouro (60 de 70, semente 42) ---------------------------------
    assert main(["amostra-ouro"]) == 0
    val = data / "validacao"
    repos_tpl = read_csv(val / "rotulos_repos_TEMPLATE.csv")
    rel_tpl = read_csv(val / "rotulos_releases_TEMPLATE.csv")
    assert len(repos_tpl) == 60 and len(rel_tpl) == 60 * 5

    # --- 3 avaliadores sintéticos: concordam, exceto 1 caso 1-1-1 ----------------
    def write(name, tipo_fn, corretiva_fn):
        for kind, tpl, cols in (("repos", repos_tpl, ["full_name", "url", "tipo_projeto", "entregas_reais"]),
                                ("releases", rel_tpl, ["full_name", "tag_name", "release_url", "corretiva"])):
            with (val / f"rotulos_{name}_{kind}.csv").open("w", newline="", encoding="utf-8") as h:
                w = csv.DictWriter(h, fieldnames=cols)
                w.writeheader()
                for i, row in enumerate(tpl):
                    row = dict(row)
                    if kind == "repos":
                        row["tipo_projeto"], row["entregas_reais"] = tipo_fn(i), "sim"
                    else:
                        row["corretiva"] = corretiva_fn(row)
                    w.writerow(row)

    truth = lambda row: "sim" if row["tag_name"] == "v1.0.1" else "nao"
    write("leo", lambda i: "biblioteca_framework", truth)
    write("gabriel", lambda i: "biblioteca_framework", truth)
    write("pedro", lambda i: "ferramenta_cli" if i == 0 else "biblioteca_framework", truth)

    assert main(["concordancia"]) == 0
    report = json.loads((val / "concordancia.json").read_text())
    assert report["dimensoes"]["corretiva"]["kappa_fleiss"] == pytest.approx(1.0)
    assert report["dimensoes"]["entregas_reais"]["kappa_fleiss"] is None      # sem variabilidade
    assert report["consenso_completo"] is True
    consenso = read_csv(val / "consenso_releases.csv")
    assert sum(r["corretiva"] == "sim" for r in consenso) == 60

    # --- heurística contra o consenso -----------------------------------------
    assert main(["heuristica"]) == 0
    versoes = {r["versao"]: r for r in read_csv(val / "heuristica_versoes.csv")}
    assert float(versoes["v1_patch"]["f1"]) == 1.0           # v1.0.1 é o único patch-bump
    chosen = json.loads((val / "heuristica_escolhida.json").read_text())
    assert chosen["f1"] == 1.0 and chosen["atinge_meta_f1_0_70"] is True

    # o dataset passa a usar a versão escolhida na validação
    assert main(["consolidate"]) == 0
    assert read_csv(data / "dataset" / "dataset_repos.csv")[0]["heuristica_versao"] == chosen["versao"]
