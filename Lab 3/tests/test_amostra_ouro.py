import csv
import json

import pandas as pd
import pytest

from src.metricas.lead_time import make_compare_key
from src.validacao.amostra_ouro import (
    build_package,
    eligible_releases,
    pick_releases,
    sample_repositories,
    write_outputs,
)

START, END = "2026-01-01T00:00:00Z", "2026-12-31T23:59:59Z"


def test_sorteio_de_60_e_reprodutivel_e_igual_ao_df_sample():
    names = [f"org/repo{i:03d}" for i in range(350)]
    first = sample_repositories(names)
    assert len(first) == 60 and len(set(first)) == 60
    assert first == sample_repositories(list(reversed(names)))   # independe da ordem de entrada
    expected = pd.DataFrame({"full_name": sorted(names)}).sample(n=60, random_state=42)["full_name"].tolist()
    assert first == expected


def test_sorteio_com_menos_de_60_repositorios_falha_com_mensagem_clara():
    with pytest.raises(ValueError, match="pelo menos 60"):
        sample_repositories([f"o/r{i}" for i in range(59)])


def make_record(n_releases=8, with_prerelease=True):
    releases, compare = [], {}
    for i in range(n_releases):
        tag = f"v1.{i}.0"
        releases.append({"id": i, "tag_name": tag, "html_url": f"https://github.com/o/r/releases/tag/{tag}",
                         "name": f"Release {i}", "body": f"notas {i}", "prerelease": False, "draft": False,
                         "published_at": f"2026-0{i + 1}-10T00:00:00Z"})
        if i > 0:
            key = make_compare_key(releases[i - 1]["published_at"], releases[i]["published_at"],
                                   releases[i - 1]["tag_name"], tag)
            compare[key] = {"complete": True, "items": [{"sha": f"s{i}", "message": f"fix: {i}", "commit": {"author": {"date": "x"}}}]}
    if with_prerelease:
        releases.append({"id": 99, "tag_name": "v9.0.0-rc1", "prerelease": True, "draft": False,
                         "published_at": "2026-05-01T00:00:00Z"})
    return {"full_name": "o/r", "html_url": "https://github.com/o/r", "language": "Go", "stars": 10,
            "_pipeline_cache": {"releases_v2": {"complete": True, "items": releases}, "compare_v1": compare}}


def test_elegiveis_excluem_prerelease_primeira_release_e_fora_da_janela():
    record = make_record()
    tags = [r["tag_name"] for r in eligible_releases(record, START, END)]
    assert "v9.0.0-rc1" not in tags
    assert "v1.0.0" not in tags                      # sem release anterior => sem compare
    assert tags == [f"v1.{i}.0" for i in range(1, 8)]
    assert eligible_releases(record, "2026-06-01T00:00:00Z", END) != []
    assert [r["tag_name"] for r in eligible_releases(record, "2026-07-01T00:00:00Z", END)] == ["v1.6.0", "v1.7.0"]


def test_pick_releases_sorteia_5_deterministicamente():
    eligible = eligible_releases(make_record(), START, END)
    a, b = pick_releases("o/r", eligible), pick_releases("o/r", eligible)
    assert a == b and len(a) == 5
    assert [r["published_at"] for r in a] == sorted(r["published_at"] for r in a)
    assert len(pick_releases("o/r", eligible[:3])) == 3          # menos de 5: usa todas


def test_pacote_nao_vaza_a_heuristica_e_traz_o_que_o_rotulador_le():
    package = build_package(["o/r"], lambda n: make_record(), START, END)
    assert len(package) == 1 and len(package[0]["releases"]) == 5
    release = package[0]["releases"][0]
    assert set(release) == {"tag_name", "url", "name", "published_at", "notes", "n_commits", "commit_messages"}
    blob = json.dumps(package).lower()
    for forbidden in ("corretiva", "is_corrective", "heuristica", "patch_bump"):
        assert forbidden not in blob


def test_arquivos_gerados_e_templates_vazios(tmp_path):
    package = build_package(["o/r"], lambda n: make_record(), START, END)
    paths = write_outputs(package, tmp_path)
    repos = list(csv.DictReader(paths["repos"].open(encoding="utf-8")))
    releases = list(csv.DictReader(paths["releases"].open(encoding="utf-8")))
    assert repos[0]["tipo_projeto"] == "" and repos[0]["entregas_reais"] == ""
    assert len(releases) == 5 and all(r["corretiva"] == "" for r in releases)
    assert releases[0]["release_url"].startswith("https://github.com/o/r/releases/tag/")
    assert json.loads(paths["pacote"].read_text(encoding="utf-8"))[0]["full_name"] == "o/r"
