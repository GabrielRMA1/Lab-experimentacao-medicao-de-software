"""Pipeline completo (coleta -> funil -> dataset) contra um GitHub falso.

Os valores esperados foram calculados à mão a partir do 'mundo' definido em
``fake_github.good_repo`` (comentários abaixo mostram as contas).
"""

import csv

import pytest

import src.collectors.repositories as repositories
from src.pipeline.config import Config
from src.pipeline.dataset import build_dataset, write_dataset
from src.pipeline.dicionario import COLUMN_NAMES
from src.pipeline.funil import build_funnel, write_funnel
from src.pipeline.selecao import collect, read_decisions
from tests.fake_github import FakeGitHub, api_release, candidate, good_repo, utc


@pytest.fixture
def cfg(tmp_path):
    return Config(observation_start="2026-01-01T00:00:00Z", observation_end="2026-06-30T23:59:59Z",
                  min_sample=1, sample_target=10, workers=2, data_dir=tmp_path / "data")


@pytest.fixture
def world():
    few = {"workflows": 1, "releases": [api_release(f"v{i}", utc(2026, 2, i + 1)) for i in range(3)],
           "runs": [], "compare": {}}
    return {"o/good": good_repo(), "o/few": few, "o/noactions": {"workflows": 0}}


@pytest.fixture
def candidates():
    return [candidate("o/good", 3000), candidate("o/few", 2000), candidate("o/noactions", 1000)]


@pytest.fixture(autouse=True)
def isolated_cache(monkeypatch, tmp_path):
    monkeypatch.setattr(repositories, "CACHE_DIR", tmp_path / "cache")
    (tmp_path / "cache").mkdir()


def run_collect(client, candidates, cfg, shard=(0, 1)):
    return collect(client, candidates, cfg, shard, log=lambda m: None)


def test_funil_e_motivos_de_descarte(world, candidates, cfg):
    stats = run_collect(FakeGitHub(world), candidates, cfg)
    assert stats["accepted"] == 1 and stats["discarded"] == 2 and stats["error"] == 0
    decisions = read_decisions(candidates, repositories.load_cached_repository)
    assert decisions["o/noactions"]["reason"] == "sem_actions"
    assert decisions["o/few"]["reason"] == "menos_de_5_releases"
    assert decisions["o/good"]["status"] == "accepted"

    funnel = build_funnel(candidates, decisions, cfg)
    n = [stage["n"] for stage in funnel["etapas"]]
    assert n == [3, 3, 2, 1, 1, 1]   # candidatos, avaliados, c/ Actions, >=5 releases, >=50 runs, final
    assert funnel["repositorios_amostra_final"] == ["o/good"] and funnel["atinge_minimo"]
    write_funnel(funnel, candidates, decisions, cfg.data_dir)
    rows = {r["full_name"]: r for r in csv.DictReader((cfg.data_dir / "selecao_repositorios.csv").open())}
    assert rows["o/good"]["situacao"] == "amostra_final" and rows["o/few"]["motivo"] == "menos_de_5_releases"
    assert "tabular" in (cfg.data_dir / "funil_tabela.tex").read_text()


def test_segunda_execucao_nao_faz_nenhuma_chamada_a_api(world, candidates, cfg):
    run_collect(FakeGitHub(world), candidates, cfg)
    again = FakeGitHub(world)
    run_collect(again, candidates, cfg)
    assert again.calls == []


def test_retomada_apos_mudar_a_janela_reavalia_com_o_cache_de_releases(world, candidates, cfg):
    run_collect(FakeGitHub(world), candidates, cfg)
    cfg.min_releases = 6   # critério novo -> decisão antiga deixa de valer
    client = FakeGitHub(world)
    stats = run_collect(client, candidates, cfg)
    assert stats["accepted"] == 0
    assert not any(c.endswith("/releases") for c in client.calls if "good" in c)  # releases vieram do cache


def test_valores_do_dataset_para_o_repositorio_bom(world, candidates, cfg):
    run_collect(FakeGitHub(world), candidates, cfg)
    rows = build_dataset(["o/good"], repositories.load_cached_repository, cfg, version="v3_patch_ou_palavras")
    row = rows[0]
    weeks = (utc(2026, 6, 30, 23, 59).timestamp() + 59 - utc(2026, 1, 1).timestamp()) / 86400 / 7

    # RQ 01: 5 releases estáveis na janela (v1.0.0, v1.0.1, v1.1.0, v1.2.0, v1.3.0); a rc não conta
    assert row["n_releases"] == 5 and row["n_prereleases_janela"] == 1
    assert row["deploy_freq_semana"] == pytest.approx(5 / weeks)
    assert row["contributors"] == 42

    # RQ 02 (a): por release = [1680 (commit antigo de 01/11!), 24, 216, 48, 24] h -> mediana 48
    assert row["lt_release_mediana_h"] == 48
    # RQ 02 (b): commits = [120, 1680, 24, 216, 24, 48, 24, 24] h -> mediana (24+48)/2 = 36
    assert row["lt_commit_mediana_h"] == 36
    assert row["lt_n_releases_avaliadas"] == 5 and row["lt_n_commits"] == 8

    # RQ 03a: 60 runs, falhas nos índices 10, 11, 40 e 59 -> 4/60
    assert (row["ci_n_falhas"], row["ci_n_sucessos"]) == (4, 56)
    assert row["cfr_ci"] == pytest.approx(4 / 60)

    # RQ 03b: v1.0.1 é corretiva (só patch + "fix:"), publicada 2 dias após v1.0.0 -> v1.0.0 falhou
    assert (row["cfr_n_avaliadas"], row["cfr_n_falhas"], row["cfr_n_censuradas"]) == (5, 1, 0)
    assert row["cfr_entrega"] == pytest.approx(0.2)
    assert row["n_releases_corretivas"] == 1 and row["rework_rate"] == pytest.approx(0.2)

    # RQ 04: episódio 1 = 6 d + 20 min = 144,33 h; episódio 2 = 3 d + 20 min = 72,33 h; o 3º (run 59) é censurado
    assert row["rec_n_episodios"] == 3 and row["rec_n_censurados"] == 1
    assert row["rec_prop_censurados"] == pytest.approx(1 / 3)
    assert row["rec_mediana_h"] == pytest.approx((144 + 20 / 60 + 72 + 20 / 60) / 2)
    assert row["coleta_incompleta"] is False


def test_csv_e_dicionario_tem_exatamente_as_mesmas_colunas(world, candidates, cfg):
    run_collect(FakeGitHub(world), candidates, cfg)
    rows = build_dataset(["o/good"], repositories.load_cached_repository, cfg, version="v1_patch")
    path = write_dataset(rows, cfg.dataset_dir)
    with path.open(newline="", encoding="utf-8") as handle:
        assert next(csv.reader(handle)) == COLUMN_NAMES


def test_compare_404_nao_derruba_a_coleta_e_e_registrado(world, candidates, cfg):
    del world["o/good"]["compare"]["v1.1.0...v1.2.0"]            # tag "reescrita"
    run_collect(FakeGitHub(world), candidates, cfg)
    row = build_dataset(["o/good"], repositories.load_cached_repository, cfg, version="v1_patch")[0]
    assert row["lt_n_releases_compare_404"] == 1 and row["lt_n_releases_avaliadas"] == 4


def test_shards_dividem_candidatos_sem_sobreposicao(world, candidates, cfg):
    a, b = FakeGitHub(world), FakeGitHub(world)
    run_collect(a, candidates, cfg, shard=(0, 2))
    run_collect(b, candidates, cfg, shard=(1, 2))
    touched_a = {c.split("/")[3] for c in a.calls}
    touched_b = {c.split("/")[3] for c in b.calls}
    assert touched_a == {"good", "noactions"} and touched_b == {"few"}


def test_coleta_para_ao_atingir_a_cota(world, cfg):
    many = {f"o/r{i}": good_repo() for i in range(6)}
    cands = [candidate(f"o/r{i}", 100 - i) for i in range(6)]
    cfg.sample_target, cfg.workers = 2, 1
    stats = collect(FakeGitHub(many), cands, cfg, log=lambda m: None)
    assert stats["accepted"] >= 2 and stats["evaluated"] < 6


def test_erro_de_api_nao_grava_decisao_e_e_retentado(world, candidates, cfg):
    client = FakeGitHub(world)
    original = client.get

    def flaky(path, params=None):
        if "compare/" in path:
            raise RuntimeError("falha de rede simulada")
        return original(path, params)

    client.get = flaky
    stats = run_collect(client, candidates, cfg)
    assert stats["error"] >= 1 and stats["accepted"] == 0
    assert "decision" not in (repositories.load_cached_repository("o/good")["_pipeline_cache"])
    client.get = original            # rede volta: a próxima execução termina
    assert run_collect(client, candidates, cfg)["accepted"] == 1
