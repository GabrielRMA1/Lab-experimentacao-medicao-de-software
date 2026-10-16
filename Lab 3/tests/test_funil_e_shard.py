import pytest

from src.pipeline.selecao import assigned_candidates, parse_shard, save_candidates, load_candidates
from tests.fake_github import candidate


def test_parse_shard():
    assert parse_shard(None) == (0, 1)
    assert parse_shard("2/3") == (1, 3)
    for bad in ("0/3", "4/3", "x"):
        with pytest.raises(ValueError):
            parse_shard(bad)


def test_fatias_cobrem_todos_os_candidatos_exatamente_uma_vez():
    cands = [candidate(f"o/r{i}", 1000 - i) for i in range(10)]
    parts = [assigned_candidates(cands, (i, 3)) for i in range(3)]
    names = [c["full_name"] for p in parts for c in p]
    assert sorted(names) == sorted(c["full_name"] for c in cands)
    assert parts[0][0]["full_name"] == "o/r0"      # ordenado por estrelas


def test_candidates_json_roundtrip_e_erro_claro_quando_falta(tmp_path):
    path = tmp_path / "candidates.json"
    with pytest.raises(FileNotFoundError, match="search"):
        load_candidates(path)
    save_candidates(path, [candidate("o/a", 5)], "stars:>1000")
    assert load_candidates(path)[0]["owner"] == {"login": "o"}
