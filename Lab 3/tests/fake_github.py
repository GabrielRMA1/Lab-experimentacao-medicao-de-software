"""API do GitHub falsa, em memória, para testar o pipeline de ponta a ponta."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from src.collectors.repositories import GitHubClient


class FakeResponse:
    def __init__(self, data: Any, status_code: int = 200, headers: dict | None = None):
        self._data, self.status_code, self.headers = data, status_code, headers or {}
        self.text = str(data)

    def json(self):
        return self._data


def iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def utc(year, month, day, hour=0, minute=0) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


def api_commit(sha: str, when: datetime, message: str) -> dict:
    return {"sha": sha, "commit": {"author": {"date": iso(when)},
                                   "committer": {"date": iso(when)}, "message": message}}


def make_runs(n: int = 60, failures=(10, 11, 40, 59), start=utc(2026, 1, 1, 10)) -> list[dict]:
    runs = []
    for i in range(n):
        started = start + timedelta(days=3 * i)
        runs.append({
            "id": 1000 + i, "workflow_id": 7, "name": "CI", "head_sha": f"h{i}",
            "head_branch": "main", "event": "push", "status": "completed",
            "conclusion": "failure" if i in failures else "success",
            "created_at": iso(started), "run_started_at": iso(started),
            "updated_at": iso(started + timedelta(minutes=20)),
        })
    return runs


class FakeGitHub(GitHubClient):
    """Substitui ``GitHubClient.get`` por respostas de um 'mundo' em memória.

    ``world[full_name]`` = dict com: workflows (int), releases (list de dicts
    da API), runs (list), compare ({"base...head": [commits]}), contributors.
    """

    def __init__(self, world: dict[str, dict]):
        super().__init__(token="fake")
        self.world = world
        self.calls: list[str] = []

    def get(self, path: str, params: dict | None = None) -> FakeResponse:
        params = params or {}
        self.calls.append(path)
        if path.startswith("https://api.github.com"):
            path = path[len("https://api.github.com"):]
        parts = path.strip("/").split("/")
        if parts[0] != "repos":
            return FakeResponse({"message": "Not Found"}, 404)
        full_name = f"{parts[1]}/{parts[2]}"
        repo = self.world.get(full_name)
        if repo is None:
            return FakeResponse({"message": "Not Found"}, 404)
        endpoint = "/".join(parts[3:])

        if endpoint == "contributors":
            last = repo.get("contributors", 1)
            link = (f'<https://api.github.com/repos/{full_name}/contributors'
                    f'?per_page=1&anon=true&page={last}>; rel="last"')
            return FakeResponse([{"login": "x"}], headers={"Link": link})
        if endpoint == "actions/workflows":
            return FakeResponse({"total_count": repo.get("workflows", 1), "workflows": []})
        if endpoint == "releases":
            return FakeResponse(repo.get("releases", []))
        if endpoint == "actions/runs":
            low, _, high = params.get("created", "0000-01-01..9999-12-31").partition("..")
            runs = [r for r in repo.get("runs", [])
                    if low <= r["created_at"][:10] <= high]
            return FakeResponse({"total_count": len(runs), "workflow_runs": runs})
        if endpoint.startswith("compare/"):
            commits = repo.get("compare", {}).get(endpoint[len("compare/"):])
            if commits is None:
                return FakeResponse({"message": "Not Found"}, 404)
            return FakeResponse({"total_commits": len(commits), "commits": commits})
        return FakeResponse({"message": "Not Found"}, 404)


def candidate(full_name: str, stars: int) -> dict:
    owner, name = full_name.split("/")
    return {"full_name": full_name, "name": name, "owner": {"login": owner},
            "html_url": f"https://github.com/{full_name}", "default_branch": "main",
            "language": "Python", "stargazers_count": stars, "forks_count": 1,
            "created_at": "2020-01-01T00:00:00Z", "updated_at": "2026-09-01T00:00:00Z",
            "archived": False, "fork": False}


def api_release(tag: str, when: datetime, prerelease=False, body="") -> dict:
    return {"id": abs(hash(tag)) % 10**6, "tag_name": tag, "name": tag, "draft": False,
            "prerelease": prerelease, "created_at": iso(when), "published_at": iso(when),
            "html_url": f"https://github.com/x/y/releases/tag/{tag}",
            "target_commitish": "main", "body": body}


def good_repo() -> dict:
    """Repositório 'bom' com resultados conhecidos (ver test_pipeline_e2e)."""
    releases = [
        api_release("v0.9.0", utc(2025, 12, 20)),
        api_release("v1.0.0", utc(2026, 1, 10)),
        api_release("v1.0.1", utc(2026, 1, 12)),
        api_release("v1.1.0", utc(2026, 2, 10)),
        api_release("v1.2.0", utc(2026, 3, 10)),
        api_release("v1.3.0", utc(2026, 4, 10)),
        api_release("v1.4.0-rc1", utc(2026, 5, 1), prerelease=True),
    ]
    compare = {
        "v0.9.0...v1.0.0": [api_commit("a1", utc(2026, 1, 5), "feat: a"),
                            api_commit("a2", utc(2025, 11, 1), "chore: antigo esquecido")],
        "v1.0.0...v1.0.1": [api_commit("b1", utc(2026, 1, 11), "fix: crash ao abrir arquivo")],
        "v1.0.1...v1.1.0": [api_commit("c1", utc(2026, 2, 1), "feat: c1"),
                            api_commit("c2", utc(2026, 2, 9), "feat: c2")],
        "v1.1.0...v1.2.0": [api_commit("d1", utc(2026, 3, 8), "feat: d1"),
                            api_commit("d2", utc(2026, 3, 9), "feat: d2")],
        "v1.2.0...v1.3.0": [api_commit("e1", utc(2026, 4, 9), "feat: e1")],
    }
    return {"workflows": 2, "releases": releases, "runs": make_runs(),
            "compare": compare, "contributors": 42}
