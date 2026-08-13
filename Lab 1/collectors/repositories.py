from github_api import run_graphql_query

REPOS_QUERY = """
query GetSampleRepos($searchQuery: String!, $limit: Int!) {
  search(
    query: $searchQuery,
    type: REPOSITORY,
    first: $limit
  ) {
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


def fetch_repositories(search_query: str, limit: int = 100):
    """Busca repositórios no GitHub de forma totalmente genérica."""
    variables = {"searchQuery": search_query, "limit": limit}

    data = run_graphql_query(REPOS_QUERY, variables=variables)

    if data and "search" in data and "nodes" in data["search"]:
        return data["search"]["nodes"]
    return []
