import argparse
import csv
import os
import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent
BASE_DIR = SRC_DIR.parent

if str(SRC_DIR) not in sys.path:
    sys.path.append(str(SRC_DIR))

from github_api import run_graphql_query


DEFAULT_OUTPUT = BASE_DIR / "snapshot_s02.csv"

PROJECT_V2_QUERY = """
query GetProjectV2Snapshot(
  $ownerLogin: String!,
  $projectNumber: Int!,
  $after: String
) {
  owner: repositoryOwner(login: $ownerLogin) {
    ... on User {
      projectV2(number: $projectNumber) {
        title
        items(first: 100, after: $after) {
          pageInfo {
            hasNextPage
            endCursor
          }
          nodes {
            id
            type
            content {
              ... on DraftIssue {
                title
              }
              ... on Issue {
                title
                number
                state
                url
                repository {
                  nameWithOwner
                }
              }
              ... on PullRequest {
                title
                number
                state
                url
                repository {
                  nameWithOwner
                }
              }
            }
            fieldValues(first: 50) {
              nodes {
                ... on ProjectV2ItemFieldSingleSelectValue {
                  name
                  field {
                    ... on ProjectV2FieldCommon {
                      name
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
    ... on Organization {
      projectV2(number: $projectNumber) {
        title
        items(first: 100, after: $after) {
          pageInfo {
            hasNextPage
            endCursor
          }
          nodes {
            id
            type
            content {
              ... on DraftIssue {
                title
              }
              ... on Issue {
                title
                number
                state
                url
                repository {
                  nameWithOwner
                }
              }
              ... on PullRequest {
                title
                number
                state
                url
                repository {
                  nameWithOwner
                }
              }
            }
            fieldValues(first: 50) {
              nodes {
                ... on ProjectV2ItemFieldSingleSelectValue {
                  name
                  field {
                    ... on ProjectV2FieldCommon {
                      name
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
"""


def get_status(item):
    for field_value in item.get("fieldValues", {}).get("nodes", []):
        field = field_value.get("field") or {}
        if field.get("name") == "Status":
            return field_value.get("name", "")
    return ""


def normalize_item(project_title, item):
    content = item.get("content") or {}
    repository = content.get("repository") or {}

    return {
        "project": project_title,
        "item_id": item.get("id", ""),
        "type": item.get("type", ""),
        "title": content.get("title", ""),
        "status": get_status(item),
        "repository": repository.get("nameWithOwner", ""),
        "number": content.get("number", ""),
        "state": content.get("state", ""),
        "url": content.get("url", ""),
    }


def fetch_project_items(owner_login, project_number):
    rows = []
    after = None

    while True:
        variables = {
            "ownerLogin": owner_login,
            "projectNumber": project_number,
            "after": after,
        }
        data = run_graphql_query(PROJECT_V2_QUERY, variables)

        owner = data.get("owner") if data else None
        project = owner.get("projectV2") if owner else None
        if not project:
            raise ValueError("Project v2 nao encontrado para o owner/numero informado.")

        project_title = project.get("title", "")
        items = project.get("items", {})

        for item in items.get("nodes", []):
            rows.append(normalize_item(project_title, item))

        page_info = items.get("pageInfo", {})
        if not page_info.get("hasNextPage"):
            break

        after = page_info.get("endCursor")

    return rows


def export_snapshot(rows, output_path):
    fieldnames = [
        "project",
        "item_id",
        "type",
        "title",
        "status",
        "repository",
        "number",
        "state",
        "url",
    ]

    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def parse_args():
    env_project_number = os.getenv("GITHUB_PROJECT_NUMBER")
    default_project_number = int(env_project_number) if env_project_number else None

    parser = argparse.ArgumentParser(
        description="Exporta snapshot de cards/status do GitHub Projects v2."
    )
    parser.add_argument(
        "--owner",
        default=os.getenv("GITHUB_PROJECT_OWNER"),
        help="Login do usuario ou organizacao dona do Project v2.",
    )
    parser.add_argument(
        "--project-number",
        type=int,
        default=default_project_number,
        help="Numero do Project v2.",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT,
        type=Path,
        help="Arquivo CSV de saida.",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    if not args.owner or not args.project_number:
        raise ValueError(
            "Informe --owner e --project-number, ou configure "
            "GITHUB_PROJECT_OWNER e GITHUB_PROJECT_NUMBER no .env."
        )

    rows = fetch_project_items(args.owner, args.project_number)
    export_snapshot(rows, args.output)

    print(f"{len(rows)} cards exportados para: {args.output}")


if __name__ == "__main__":
    main()
