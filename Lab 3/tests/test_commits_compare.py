import pytest

import src.collectors.repositories as repositories
from src.collectors.commits_compare import (
    collect_release_commits,
    collect_window_commits,
    normalize_compare_commit,
    releases_to_compare,
    sort_published_releases,
)
from src.collectors.repositories import GitHubClient, load_cached_repository

REPO = {"full_name": "o/r", "owner": "o", "name": "r", "default_branch": "main"}


class FakeResponse:
    def __init__(self, data, headers=None, status_code=200, text="fake"):
        self._data, self.headers, self.status_code, self.text = data, headers or {}, status_code, text

    def json(self):
        return self._data


def release(tag, published, prerelease=False, rid=None):
    return {"id": rid or hash(tag) % 1000, "tag_name": tag, "published_at": published,
            "prerelease": prerelease, "draft": False}


def api_commit(sha, date, message):
    return {"sha": sha, "commit": {"author": {"date": date}, "committer": {"date": date},
                                   "message": message}}


@pytest.fixture(autouse=True)
def isolated_cache(monkeypatch, tmp_path):
    monkeypatch.setattr(repositories, "CACHE_DIR", tmp_path)


def test_normalize_mantem_data_do_autor_e_so_a_primeira_linha_da_mensagem():
    out = normalize_compare_commit(api_commit("s1", "2026-01-02T00:00:00Z", "fix: a\n\ncorpo longo"))
    assert out == {"sha": "s1", "message": "fix: a",
                   "commit": {"author": {"date": "2026-01-02T00:00:00Z"},
                              "committer": {"date": "2026-01-02T00:00:00Z"}}}


def test_commit_antigo_authorado_antes_da_release_anterior_e_mantido(monkeypatch):
    """Regressão da S01: filtrar por data de autor descartava este commit."""
    calls = []

    def fake_get(url, **kwargs):
        calls.append((url, kwargs.get("params")))
        return FakeResponse({"total_commits": 1, "commits": [
            api_commit("old", "2025-01-01T00:00:00Z", "feat: escrito há meses")]})

    monkeypatch.setattr("src.collectors.repositories.requests.get", fake_get)
    result = collect_release_commits(
        GitHubClient(token="t"), REPO,
        release("v1.0.0", "2026-03-01T00:00:00Z"), release("v1.1.0", "2026-03-15T00:00:00Z"))
    assert calls[0][0] == "https://api.github.com/repos/o/r/compare/v1.0.0...v1.1.0"
    assert [c["sha"] for c in result["items"]] == ["old"]
    assert result["not_found"] is False


def test_compare_pagina_via_link_e_usa_cache_na_segunda_chamada(monkeypatch):
    page2 = "https://api.github.com/repos/o/r/compare/v1.0.0...v1.1.0?page=2&per_page=100"
    pages = [
        FakeResponse({"commits": [api_commit("a", "2026-03-02T00:00:00Z", "x")]},
                     headers={"Link": f'<{page2}>; rel="next"'}),
        FakeResponse({"commits": [api_commit("b", "2026-03-03T00:00:00Z", "y")]}),
    ]
    calls = []

    def fake_get(url, **kwargs):
        calls.append(url)
        return pages[len(calls) - 1]

    monkeypatch.setattr("src.collectors.repositories.requests.get", fake_get)
    args = (GitHubClient(token="t"), REPO,
            release("v1.0.0", "2026-03-01T00:00:00Z"), release("v1.1.0", "2026-03-15T00:00:00Z"))
    first = collect_release_commits(*args)
    assert [c["sha"] for c in first["items"]] == ["a", "b"] and len(calls) == 2

    monkeypatch.setattr("src.collectors.repositories.requests.get",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("cache")))
    assert collect_release_commits(*args)["items"] == first["items"]


def test_compare_404_vira_not_found_e_nao_repete_a_chamada(monkeypatch):
    n = {"calls": 0}

    def fake_get(url, **kwargs):
        n["calls"] += 1
        return FakeResponse({"message": "Not Found"}, status_code=404, text="Not Found")

    monkeypatch.setattr("src.collectors.repositories.requests.get", fake_get)
    args = (GitHubClient(token="t"), REPO,
            release("v1.0.0", "2026-03-01T00:00:00Z"), release("gone", "2026-03-15T00:00:00Z"))
    assert collect_release_commits(*args) == {"items": [], "not_found": True}
    assert collect_release_commits(*args) == {"items": [], "not_found": True}
    assert n["calls"] == 1
    state = list(load_cached_repository("o/r")["_pipeline_cache"]["compare_v1"].values())[0]
    assert state["not_found"] is True and state["complete"] is True


def test_erro_inesperado_propaga(monkeypatch):
    monkeypatch.setattr("src.collectors.repositories.requests.get",
                        lambda *a, **k: FakeResponse({}, status_code=400, text="bad"))
    with pytest.raises(RuntimeError, match="400"):
        collect_release_commits(
            GitHubClient(token="t"), REPO,
            release("v1", "2026-03-01T00:00:00Z"), release("v2", "2026-03-15T00:00:00Z"))


def test_pares_incluem_release_anterior_fora_da_janela_e_ignoram_prerelease():
    releases = [
        release("v0.9.0", "2025-12-20T00:00:00Z"),            # fora da janela
        release("v1.0.0", "2026-01-10T00:00:00Z"),
        release("v1.1.0-rc1", "2026-01-15T00:00:00Z", prerelease=True),
        release("v1.1.0", "2026-02-10T00:00:00Z"),
    ]
    pairs = releases_to_compare(releases, "2026-01-01T00:00:00Z", "2026-12-31T23:59:59Z")
    assert [(a["tag_name"], b["tag_name"]) for a, b in pairs] == [
        ("v0.9.0", "v1.0.0"), ("v1.0.0", "v1.1.0")]


def test_primeira_release_da_historia_nao_gera_par():
    releases = [release("v1.0.0", "2026-01-10T00:00:00Z")]
    assert releases_to_compare(releases, "2026-01-01T00:00:00Z", "2026-12-31T23:59:59Z") == []


def test_collect_window_commits_resume_erros_e_404(monkeypatch):
    def fake_get(url, **kwargs):
        if "v1.0.0...v1.1.0" in url:
            return FakeResponse({"commits": [api_commit("a", "2026-02-01T00:00:00Z", "x")]})
        if "v1.1.0...v1.2.0" in url:
            return FakeResponse({}, status_code=404, text="nf")
        return FakeResponse({}, status_code=400, text="boom")

    monkeypatch.setattr("src.collectors.repositories.requests.get", fake_get)
    releases = [release(t, d) for t, d in [
        ("v1.0.0", "2026-01-10T00:00:00Z"), ("v1.1.0", "2026-02-10T00:00:00Z"),
        ("v1.2.0", "2026-03-10T00:00:00Z"), ("v1.3.0", "2026-04-10T00:00:00Z")]]
    summary = collect_window_commits(GitHubClient(token="t"), REPO, releases,
                                     "2026-01-01T00:00:00Z", "2026-12-31T23:59:59Z")
    assert summary["n_pairs"] == 3 and summary["n_not_found"] == 1
    assert len(summary["errors"]) == 1 and "v1.3.0" in summary["errors"][0]


def test_sort_published_releases_ignora_draft_e_sem_data():
    items = [release("b", "2026-02-01T00:00:00Z"), release("a", "2026-01-01T00:00:00Z"),
             {"tag_name": "d", "published_at": None, "draft": False},
             {"tag_name": "e", "published_at": "2026-03-01T00:00:00Z", "draft": True}]
    assert [r["tag_name"] for r in sort_published_releases(items)] == ["a", "b"]
