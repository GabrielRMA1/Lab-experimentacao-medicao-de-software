import pytest

from src.collectors.repositories import (
    GitHubClient,
    build_initial_funnel,
    collect_cached_paginated,
    collect_repository_commits,
    collect_repository_metadata,
    collect_repository_releases,
    collect_repository_workflow_runs,
    filter_records_by_observation_window,
    load_cached_repository,
    save_cached_repository,
)


class FakeResponse:
    def __init__(self, data, headers=None, status_code=200):
        self.status_code = status_code
        self._data = data
        self.headers = headers or {}
        self.text = "fake response"

    def json(self):
        return self._data


@pytest.fixture
def published_release_pages():
    return [
        FakeResponse(
            [
                {
                    "id": 1,
                    "tag_name": "v1.0.0",
                    "name": "First release",
                    "created_at": "2025-01-01T10:00:00Z",
                    "published_at": "2025-01-02T10:00:00Z",
                    "html_url": "https://github.com/example/project/releases/tag/v1.0.0",
                    "target_commitish": "main",
                    "prerelease": False,
                    "draft": False,
                },
                {
                    "id": 2,
                    "tag_name": "v2.0.0-draft",
                    "draft": True,
                },
            ],
            headers={
                "Link": (
                    '<https://api.github.com/repos/example/project/releases?page=2&per_page=100>; '
                    'rel="next", '
                    '<https://api.github.com/repos/example/project/releases?page=2&per_page=100>; '
                    'rel="last"'
                )
            },
        ),
        FakeResponse(
            [
                {
                    "id": 3,
                    "tag_name": "v0.9.0",
                    "name": "Previous release",
                    "created_at": "2024-12-01T10:00:00Z",
                    "published_at": "2024-12-02T10:00:00Z",
                    "html_url": "https://github.com/example/project/releases/tag/v0.9.0",
                    "target_commitish": "main",
                    "prerelease": True,
                    "draft": False,
                }
            ]
        ),
    ]


@pytest.fixture
def commit_pages():
    return [
        FakeResponse(
            [
                {
                    "sha": "author-date-in-range",
                    "commit": {
                        "author": {"date": "2025-01-05T12:00:00Z"},
                        "committer": {"date": "2025-01-12T12:00:00Z"},
                    },
                },
                {
                    "sha": "author-date-out-of-range",
                    "commit": {
                        "author": {"date": "2024-12-31T23:59:59Z"},
                        "committer": {"date": "2025-01-05T12:00:00Z"},
                    },
                },
            ],
            headers={
                "Link": (
                    '<https://api.github.com/repos/example/project/commits?page=2&per_page=100>; '
                    'rel="next", '
                    '<https://api.github.com/repos/example/project/commits?page=2&per_page=100>; '
                    'rel="last"'
                )
            },
        ),
        FakeResponse(
            [
                {
                    "sha": "author-date-at-end",
                    "commit": {
                        "author": {"date": "2025-01-10T00:00:00Z"},
                        "committer": {},
                    },
                }
            ]
        ),
    ]


@pytest.fixture
def workflow_run_pages():
    def run(run_id, branch, event, conclusion):
        return {
            "id": run_id,
            "head_sha": f"sha-{run_id}",
            "head_branch": branch,
            "event": event,
            "status": "completed",
            "conclusion": conclusion,
            "created_at": "2025-01-01T10:00:00Z",
            "updated_at": "2025-01-01T10:05:00Z",
            "run_started_at": "2025-01-01T10:01:00Z",
        }

    return [
        FakeResponse(
            {
                "total_count": 8,
                "workflow_runs": [
                    run(1, "main", "push", "success"),
                    run(2, "main", "push", "failure"),
                    run(3, "feature", "push", "failure"),
                    run(4, "main", "pull_request", "failure"),
                ],
            },
            headers={
                "Link": (
                    '<https://api.github.com/repos/example/project/actions/runs?page=2&per_page=100>; '
                    'rel="next", '
                    '<https://api.github.com/repos/example/project/actions/runs?page=2&per_page=100>; '
                    'rel="last"'
                )
            },
        ),
        FakeResponse(
            {
                "total_count": 8,
                "workflow_runs": [
                    run(5, "main", "push", "timed_out"),
                    run(6, "main", "push", "startup_failure"),
                    run(7, "main", "push", "cancelled"),
                    run(8, "main", "push", "skipped"),
                ],
            }
        ),
    ]


@pytest.fixture(autouse=True)
def isolate_repository_cache(monkeypatch, tmp_path):
    monkeypatch.setattr("src.collectors.repositories.CACHE_DIR", tmp_path)


def test_build_initial_funnel_counts_candidates():
    candidates = [{"full_name": "a/a"}, {"full_name": "b/b"}]
    metadata = [{"full_name": "a/a"}, {"full_name": "b/b"}]

    funnel = build_initial_funnel(candidates, metadata)

    assert funnel["candidates_found"] == 2
    assert funnel["metadata_collected"] == 2
    assert funnel["stages"][0]["name"] == "candidates"
    assert funnel["stages"][1]["count"] == 2


def funnel_repository(
    name="example/project",
    release_count=5,
    run_count=50,
    releases=None,
    workflow_runs=None,
):
    return {
        "full_name": name,
        "default_branch": "main",
        "releases": releases if releases is not None else [
            {
                "id": index,
                "draft": False,
                "prerelease": False,
                "published_at": "2025-06-01T00:00:00Z",
            }
            for index in range(release_count)
        ],
        "workflow_runs": workflow_runs if workflow_runs is not None else [
            {
                "id": index,
                "head_branch": "main",
                "event": "push",
                "created_at": "2025-06-01T00:00:00Z",
            }
            for index in range(run_count)
        ],
    }


def test_funnel_requires_five_published_non_draft_non_prerelease_releases():
    candidates = [{"full_name": "example/project"}]
    repository = funnel_repository(
        releases=[
            {
                "id": 1,
                "draft": False,
                "prerelease": False,
                "published_at": "2025-06-01T00:00:00Z",
            },
            *[
                {
                    "id": index,
                    "draft": True,
                    "prerelease": False,
                    "published_at": "2025-06-01T00:00:00Z",
                }
                for index in range(2, 5)
            ],
            {
                "id": 5,
                "draft": False,
                "prerelease": True,
                "published_at": "2025-06-01T00:00:00Z",
            },
        ],
    )

    funnel = build_initial_funnel(candidates, [repository])

    assert funnel["minimum_releases_and_runs"]["count"] == 0
    assert funnel["minimum_releases_and_runs"]["discarded_by_reason"][
        "fewer_than_5_releases"
    ] == 1


def test_funnel_requires_at_least_fifty_workflow_runs():
    candidates = [{"full_name": "example/project"}]
    repository = funnel_repository(run_count=49)

    funnel = build_initial_funnel(candidates, [repository])

    assert funnel["minimum_releases_and_runs"]["count"] == 0
    assert funnel["minimum_releases_and_runs"]["discarded_by_reason"][
        "fewer_than_50_workflow_runs"
    ] == 1


def test_funnel_counts_only_default_branch_push_runs_for_actions():
    candidates = [{"full_name": "example/project"}]
    repository = funnel_repository(
        run_count=0,
        workflow_runs=[
            {
                "id": 1,
                "head_branch": "feature",
                "event": "push",
                "created_at": "2025-06-01T00:00:00Z",
            },
            {
                "id": 2,
                "head_branch": "main",
                "event": "pull_request",
                "created_at": "2025-06-01T00:00:00Z",
            },
        ],
    )

    funnel = build_initial_funnel(candidates, [repository])

    assert funnel["with_actions"]["count"] == 0
    assert funnel["with_actions"]["discarded_by_reason"][
        "no_valid_workflow_runs"
    ] == 1


def test_funnel_limits_final_sample_to_s01_target():
    candidates = [
        {"full_name": f"example/project-{index}"}
        for index in range(3)
    ]
    repositories = [
        funnel_repository(name=candidate["full_name"])
        for candidate in candidates
    ]

    funnel = build_initial_funnel(candidates, repositories, sample_target=2)

    assert funnel["final_sample"]["count"] == 2
    assert funnel["final_sample"]["target"] == 2
    assert funnel["final_sample"]["repository_names"] == [
        "example/project-0",
        "example/project-1",
    ]


def test_funnel_reports_unconfigured_observation_window_without_inventing_dates():
    funnel = build_initial_funnel([], [])

    assert funnel["observation_window"] == {
        "required_months": 12,
        "start": None,
        "end": None,
        "configured": False,
        "status": "not_configured",
        "note": funnel["observation_window"]["note"],
    }
    assert "aplicados" in funnel["observation_window"]["note"]


def test_funnel_applies_configured_observation_window():
    candidates = [{"full_name": "example/project"}]
    repository = funnel_repository(
        releases=[
            {
                "id": index,
                "draft": False,
                "prerelease": False,
                "published_at": "2025-06-01T00:00:00Z",
            }
            for index in range(5)
        ],
        workflow_runs=[
            {
                "id": index,
                "head_branch": "main",
                "event": "push",
                "created_at": "2025-06-01T00:00:00Z",
            }
            for index in range(50)
        ],
    )
    repository["releases"].append(
        {
            "id": 6,
            "draft": False,
            "prerelease": False,
            "published_at": "2024-01-01T00:00:00Z",
        }
    )

    funnel = build_initial_funnel(
        candidates,
        [repository],
        observation_start="2025-01-01T00:00:00Z",
        observation_end="2025-12-31T23:59:59Z",
    )

    assert funnel["minimum_releases_and_runs"]["count"] == 1
    assert funnel["observation_window"]["configured"] is True


@pytest.mark.parametrize(
    ("date_path", "records"),
    [
        (
            ("published_at",),
            [
                {"id": 1, "published_at": "2025-10-01T23:59:59Z"},
                {"id": 2, "published_at": "2025-10-02T00:00:00Z"},
                {"id": 3, "published_at": "2026-10-03T00:00:00Z"},
            ],
        ),
        (
            ("commit", "author", "date"),
            [
                {"sha": "old", "commit": {"author": {"date": "2025-10-01T23:59:59Z"}}},
                {"sha": "inside", "commit": {"author": {"date": "2026-03-04T12:00:00Z"}}},
                {"sha": "new", "commit": {"author": {"date": "2026-10-03T00:00:00Z"}}},
            ],
        ),
        (
            ("created_at",),
            [
                {"id": 1, "created_at": "2025-10-01T23:59:59Z"},
                {"id": 2, "created_at": "2026-10-02T23:59:59Z"},
                {"id": 3, "created_at": "2026-10-03T00:00:00Z"},
            ],
        ),
    ],
)
def test_observation_window_filters_releases_commits_and_workflow_runs(
    date_path,
    records,
):
    filtered = filter_records_by_observation_window(
        records,
        date_path,
        "2025-10-02T00:00:00Z",
        "2026-10-02T23:59:59Z",
    )

    assert filtered == [records[1]]


def test_observation_window_requires_both_dates():
    with pytest.raises(ValueError, match="juntos"):
        filter_records_by_observation_window(
            [],
            ("published_at",),
            "2025-10-02T00:00:00Z",
            None,
        )


def test_collect_repository_releases_paginates_and_excludes_drafts(
    monkeypatch,
    published_release_pages,
):
    requested_urls = []

    def fake_get(url, **kwargs):
        requested_urls.append(url)
        return published_release_pages[len(requested_urls) - 1]

    monkeypatch.setattr("src.collectors.repositories.requests.get", fake_get)
    client = GitHubClient(token="test-token")

    releases = collect_repository_releases(
        client,
        {"full_name": "example/project", "owner": "example", "name": "project"},
    )

    assert len(requested_urls) == 2
    assert requested_urls[0] == "https://api.github.com/repos/example/project/releases"
    assert requested_urls[1].endswith("page=2&per_page=100")
    assert [release["id"] for release in releases] == [1]
    assert releases[0]["published_at"] == "2025-01-02T10:00:00Z"
    assert all(release["draft"] is False for release in releases)
    assert all(release["prerelease"] is False for release in releases)


def test_collect_repository_commits_paginates_and_filters_by_author_date(
    monkeypatch,
    commit_pages,
):
    requests_made = []

    def fake_get(url, **kwargs):
        requests_made.append((url, kwargs.get("params")))
        return commit_pages[len(requests_made) - 1]

    monkeypatch.setattr("src.collectors.repositories.requests.get", fake_get)
    client = GitHubClient(token="test-token")

    commits = collect_repository_commits(
        client,
        {
            "full_name": "example/project",
            "owner": "example",
            "name": "project",
            "default_branch": "trunk",
        },
        since="2025-01-01T00:00:00Z",
        until="2025-01-10T00:00:00Z",
    )

    assert len(requests_made) == 2
    assert requests_made[0][0] == "https://api.github.com/repos/example/project/commits"
    assert requests_made[0][1] == {
        "sha": "trunk",
        "since": "2025-01-01T00:00:00Z",
        "until": "2025-01-10T00:00:00Z",
        "per_page": 100,
    }
    assert requests_made[1][0].endswith("page=2&per_page=100")
    assert [commit["sha"] for commit in commits] == [
        "author-date-in-range",
        "author-date-at-end",
    ]
    assert commits[0]["commit"]["author"]["date"] == "2025-01-05T12:00:00Z"
    assert commits[0]["commit"]["committer"]["date"] == "2025-01-12T12:00:00Z"
    assert "committer" not in commits[1]["commit"]


def test_collect_repository_workflow_runs_paginates_filters_and_classifies(
    monkeypatch,
    workflow_run_pages,
):
    requests_made = []

    def fake_get(url, **kwargs):
        requests_made.append((url, kwargs.get("params")))
        return workflow_run_pages[len(requests_made) - 1]

    monkeypatch.setattr("src.collectors.repositories.requests.get", fake_get)
    client = GitHubClient(token="test-token")

    runs = collect_repository_workflow_runs(
        client,
        {
            "full_name": "example/project",
            "owner": "example",
            "name": "project",
            "default_branch": "main",
        },
    )

    assert len(requests_made) == 2
    assert requests_made[0][0] == (
        "https://api.github.com/repos/example/project/actions/runs"
    )
    assert requests_made[0][1] == {
        "branch": "main",
        "event": "push",
        "per_page": 100,
    }
    assert requests_made[1][0].endswith("page=2&per_page=100")
    assert [run["id"] for run in runs] == [1, 2, 5, 6, 7, 8]
    assert [run["classification"] for run in runs] == [
        "success",
        "failure",
        "failure",
        "failure",
        "ignored",
        "ignored",
    ]
    assert runs[0]["head_sha"] == "sha-1"
    assert runs[0]["head_branch"] == "main"
    assert runs[0]["event"] == "push"
    assert runs[0]["status"] == "completed"
    assert runs[0]["conclusion"] == "success"
    assert runs[0]["created_at"] == "2025-01-01T10:00:00Z"
    assert runs[0]["updated_at"] == "2025-01-01T10:05:00Z"
    assert runs[0]["run_started_at"] == "2025-01-01T10:01:00Z"


def test_repository_cache_can_be_written_and_read(monkeypatch, tmp_path):
    monkeypatch.setattr("src.collectors.repositories.CACHE_DIR", tmp_path)
    cached = {"full_name": "example/project", "stars": 42}

    save_cached_repository(cached)

    assert load_cached_repository("example/project") == cached


def test_metadata_read_hides_internal_collection_cache(monkeypatch, tmp_path):
    monkeypatch.setattr("src.collectors.repositories.CACHE_DIR", tmp_path)
    save_cached_repository(
        {
            "full_name": "example/project",
            "stars": 42,
            "_pipeline_cache": {"releases": {"items": [], "complete": True}},
        }
    )

    metadata = collect_repository_metadata(
        client=None,
        repository={"full_name": "example/project"},
    )

    assert metadata == {"full_name": "example/project", "stars": 42}


def test_github_client_reads_documented_token_name(monkeypatch):
    monkeypatch.setenv("GITHUBTOKEN", "unit-test-token")
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    assert GitHubClient().token == "unit-test-token"


def test_cached_stage_does_not_call_github_api(monkeypatch, tmp_path):
    monkeypatch.setattr("src.collectors.repositories.CACHE_DIR", tmp_path)
    save_cached_repository(
        {
            "full_name": "example/project",
            "_pipeline_cache": {
                "releases": {
                    "items": [{"id": 1, "tag_name": "v1.0.0"}],
                    "next_url": None,
                    "complete": True,
                }
            },
        }
    )

    class NoCallClient:
        def get_paginated(self, *args, **kwargs):
            raise AssertionError("A API não deveria ser chamada")

    assert collect_cached_paginated(
        NoCallClient(),
        "example/project",
        "/repos/example/project/releases",
        cache_key="releases",
        params={"per_page": 100},
    ) == [{"id": 1, "tag_name": "v1.0.0"}]


def test_cached_collection_resumes_after_interrupted_page(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr("src.collectors.repositories.CACHE_DIR", tmp_path)
    next_page_url = (
        "https://api.github.com/repos/example/project/releases?page=2&per_page=100"
    )
    first_call_urls = []

    def fail_on_second_page(url, **kwargs):
        first_call_urls.append(url)
        if len(first_call_urls) == 1:
            return FakeResponse(
                [{"id": 1}],
                headers={"Link": f'<{next_page_url}>; rel="next"'},
            )
        return FakeResponse([], status_code=500)

    monkeypatch.setattr("src.collectors.repositories.requests.get", fail_on_second_page)
    client = GitHubClient(token="test-token")

    with pytest.raises(RuntimeError, match="500"):
        collect_cached_paginated(
            client,
            "example/project",
            "/repos/example/project/releases",
            cache_key="releases",
            params={"per_page": 100},
        )

    partial = load_cached_repository("example/project")
    assert partial["_pipeline_cache"]["releases"] == {
        "items": [{"id": 1}],
        "next_url": next_page_url,
        "complete": False,
    }

    resumed_urls = []

    def finish_on_second_page(url, **kwargs):
        resumed_urls.append(url)
        return FakeResponse([{"id": 2}])

    monkeypatch.setattr("src.collectors.repositories.requests.get", finish_on_second_page)
    assert collect_cached_paginated(
        client,
        "example/project",
        "/repos/example/project/releases",
        cache_key="releases",
        params={"per_page": 100},
    ) == [{"id": 1}, {"id": 2}]
    assert resumed_urls == [next_page_url]

    def unexpected_request(*args, **kwargs):
        raise AssertionError("A etapa concluída não deve ser coletada novamente")

    monkeypatch.setattr("src.collectors.repositories.requests.get", unexpected_request)
    assert collect_cached_paginated(
        client,
        "example/project",
        "/repos/example/project/releases",
        cache_key="releases",
        params={"per_page": 100},
    ) == [{"id": 1}, {"id": 2}]
