def _get_total_count(data: dict) -> int:
    if data and "totalCount" in data:
        return data["totalCount"]
    return 0


def process_rq07(total_issues_data: dict, closed_issues_data: dict) -> dict:
    total_issues = _get_total_count(total_issues_data)
    closed_issues = _get_total_count(closed_issues_data)

    if total_issues == 0:
        percentual_fechadas = 0
    else:
        percentual_fechadas = round((closed_issues / total_issues) * 100, 2)

    return {
        "total_issues": total_issues,
        "issues_fechadas": closed_issues,
        "percentual_issues_fechadas": percentual_fechadas,
    }
