"""Novidades do cliente/coletor na S02."""

import pytest

import src.collectors.repositories as repositories
from src.collectors.repositories import (
    GitHubClient,
    collect_repository_releases_full,
    get_contributor_count,
    get_pipeline_value,
    get_workflow_count,
    search_repositories_sliced,
    set_pipeline_value,
)


class FakeResponse:
    def __init__(self, data, headers=None, status_code=200, text="fake"):
        self._data, self.headers, self.status_code, self.text = data, headers or {}, status_code, text

    def json(self):
        return self._data


@pytest.fixture(autouse=True)
def isolated_cache(monkeypatch, tmp_path):
    monkeypatch.setattr(repositories, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(repositories.time, "sleep", lambda s: None)


def test_token_aceita_github_token_como_alternativa(monkeypatch):
    monkeypatch.delenv("GITHUBTOKEN", raising=False)
    monkeypatch.setenv("GITHUB_TOKEN", "alt")
    assert GitHubClient().token == "alt"


def test_sem_token_falha_com_mensagem_util(monkeypatch):
    monkeypatch.delenv("GITHUBTOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    with pytest.raises(RuntimeError, match="GITHUBTOKEN"):
        GitHubClient()


def test_limite_secundario_respeita_retry_after(monkeypatch):
    sleeps, responses = [], [
        FakeResponse({}, headers={"Retry-After": "7", "X-RateLimit-Remaining": "4000"}, status_code=403),
        FakeResponse({"ok": True}),
    ]
    monkeypatch.setattr(repositories.time, "sleep", sleeps.append)
    monkeypatch.setattr("src.collectors.repositories.requests.get", lambda *a, **k: responses.pop(0))
    assert GitHubClient(token="t").get("/x").json() == {"ok": True}
    assert sleeps == [8]


def test_limite_primario_espera_ate_o_reset(monkeypatch):
    sleeps, responses = [], [
        FakeResponse({}, headers={"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "1000"}, status_code=403),
        FakeResponse({"ok": 1}),
    ]
    monkeypatch.setattr(repositories.time, "sleep", sleeps.append)
    monkeypatch.setattr(repositories.time, "time", lambda: 990)
    monkeypatch.setattr("src.collectors.repositories.requests.get", lambda *a, **k: responses.pop(0))
    GitHubClient(token="t").get("/x")
    assert sleeps == [11]


def test_contribuidores_vem_da_ultima_pagina_do_link_em_uma_chamada(monkeypatch):
    calls = []

    def fake_get(url, **kwargs):
        calls.append(kwargs["params"])
        return FakeResponse([{"login": "a"}], headers={"Link": (
            '<https://api.github.com/repos/o/r/contributors?per_page=1&anon=true&page=2>; rel="next", '
            '<https://api.github.com/repos/o/r/contributors?per_page=1&anon=true&page=1234>; rel="last"')})

    monkeypatch.setattr("src.collectors.repositories.requests.get", fake_get)
    assert get_contributor_count(GitHubClient(token="t"), "o", "r") == 1234
    assert calls == [{"anon": "true", "per_page": 1}]


def test_contribuidores_sem_link_conta_a_lista_e_204_e_zero(monkeypatch):
    monkeypatch.setattr("src.collectors.repositories.requests.get",
                        lambda *a, **k: FakeResponse([{"login": "a"}]))
    assert get_contributor_count(GitHubClient(token="t"), "o", "r") == 1
    monkeypatch.setattr("src.collectors.repositories.requests.get",
                        lambda *a, **k: FakeResponse(None, status_code=204))
    assert get_contributor_count(GitHubClient(token="t"), "o", "r") == 0


def test_contribuidores_lista_grande_cai_para_stats(monkeypatch):
    def fake_get(url, **kwargs):
        if "/stats/" not in url:
            return FakeResponse({}, status_code=403, text="The history or contributor list is too large")
        return FakeResponse([{}, {}, {}])

    monkeypatch.setattr("src.collectors.repositories.requests.get", fake_get)
    assert get_contributor_count(GitHubClient(token="t"), "o", "r") == 3


def test_workflow_count(monkeypatch):
    monkeypatch.setattr("src.collectors.repositories.requests.get",
                        lambda *a, **k: FakeResponse({"total_count": 0, "workflows": []}))
    assert get_workflow_count(GitHubClient(token="t"), "o", "r") == 0
    monkeypatch.setattr("src.collectors.repositories.requests.get",
                        lambda *a, **k: FakeResponse({}, status_code=404))
    assert get_workflow_count(GitHubClient(token="t"), "o", "r") == 0


def test_busca_fatiada_ultrapassa_o_teto_de_1000_resultados(monkeypatch):
    """Cada fatia devolve até 1000; a seguinte começa nas estrelas do último item."""
    universe = [{"full_name": f"o/r{i}", "stargazers_count": 100_000 - i * 10} for i in range(2500)]
    queries = []

    def fake_get(url, **kwargs):
        q = kwargs["params"]["q"]
        queries.append(q)
        if "stars:>=" in q:
            lo, hi = int(q.split(">=")[1]), 10**9
        else:
            lo, hi = map(int, q.split("stars:")[1].split(".."))
        matching = [r for r in universe if lo <= r["stargazers_count"] <= hi]
        page, per = kwargs["params"]["page"], kwargs["params"]["per_page"]
        return FakeResponse({"items": matching[(page - 1) * per: page * per]})

    monkeypatch.setattr("src.collectors.repositories.requests.get", fake_get)
    result = search_repositories_sliced(GitHubClient(token="t"), "language:python stars:>1000", target=2400, min_stars=1000)
    assert len(result) == 2400 == len({r["full_name"] for r in result})
    assert [r["stargazers_count"] for r in result] == sorted((r["stargazers_count"] for r in result), reverse=True)
    assert all(q.startswith("language:python stars:") for q in queries)   # qualificadores extras mantidos
    assert not any("stars:>1000" in q for q in queries)                    # a parte de estrelas é recalculada


def test_busca_fatiada_para_quando_a_fatia_nao_satura(monkeypatch):
    monkeypatch.setattr("src.collectors.repositories.requests.get",
                        lambda *a, **k: FakeResponse({"items": [{"full_name": "o/a", "stargazers_count": 5000}]}))
    assert len(search_repositories_sliced(GitHubClient(token="t"), target=1500)) == 1


def test_releases_full_mantem_prerelease_corpo_truncado_e_descarta_draft(monkeypatch):
    payload = [
        {"id": 1, "tag_name": "v1", "draft": False, "prerelease": False, "published_at": "2026-01-01T00:00:00Z", "body": "x" * 5000},
        {"id": 2, "tag_name": "v2-rc", "draft": False, "prerelease": True, "published_at": "2026-01-02T00:00:00Z"},
        {"id": 3, "tag_name": "v3", "draft": True},
    ]
    monkeypatch.setattr("src.collectors.repositories.requests.get", lambda *a, **k: FakeResponse(payload))
    releases = collect_repository_releases_full(GitHubClient(token="t"), {"full_name": "o/r", "owner": "o", "name": "r"})
    assert [r["tag_name"] for r in releases] == ["v1", "v2-rc"]
    assert releases[1]["prerelease"] is True and len(releases[0]["body"]) == 2000


def test_pipeline_value_roundtrip_nao_apaga_outros_dados():
    repositories.save_cached_repository({"full_name": "o/r", "stars": 3})
    set_pipeline_value("o/r", "workflows_count", 4)
    assert get_pipeline_value("o/r", "workflows_count") == 4
    assert get_pipeline_value("o/r", "ausente", default="d") == "d"
    assert repositories.load_cached_repository("o/r")["stars"] == 3
