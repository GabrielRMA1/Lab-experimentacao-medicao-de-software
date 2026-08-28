from github_api import run_graphql_query

REPOS_QUERY = """
query GetSampleRepos($searchQuery: String!, $limit: Int!, $cursor: String) {
  search(
    query: $searchQuery,
    type: REPOSITORY,
    first: $limit,
    after: $cursor
  ) {
    pageInfo {
      hasNextPage
      endCursor
    }
    nodes {
      ... on Repository {
        nameWithOwner
        createdAt
        pushedAt
        primaryLanguage {
          name
        }
        stargazerCount
        mergedPRs: pullRequests(states: MERGED) {
          totalCount
        }
        releases {
          totalCount
        }
        totalIssues: issues {
          totalCount
        }
        closedIssues: issues(states: CLOSED) {
          totalCount
        }
      }
    }
  }
}
"""


def fetch_repositories(
    search_query: str, limit: int = 100, page_size: int = 20
):
    """Busca ate ``limit`` repositorios em paginas menores usando cursores."""
    if limit <= 0:
        return []
    if page_size <= 0 or page_size > 100:
        raise ValueError("page_size deve estar entre 1 e 100")

    repositories = []
    cursor = None

    while len(repositories) < limit:
        remaining = limit - len(repositories)
        variables = {
            "searchQuery": search_query,
            "limit": min(page_size, remaining),
            "cursor": cursor,
        }
        data = run_graphql_query(REPOS_QUERY, variables=variables)
        search_result = data.get("search") if data else None

        if not search_result or "nodes" not in search_result:
            break

        repositories.extend(
            repository for repository in search_result["nodes"] if repository
        )

        page_info = search_result.get("pageInfo", {})
        if not page_info.get("hasNextPage") or not page_info.get("endCursor"):
            break

        cursor = page_info["endCursor"]

    return repositories[:limit]
