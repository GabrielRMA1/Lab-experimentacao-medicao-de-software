def process_rq10(merged_prs: int, closed_issues: int):
    """Calcula a proporcao de PRs mescladas por issue fechada.

    A metrica e indefinida quando o repositorio nao possui issues fechadas.
    """
    merged_prs = merged_prs or 0
    closed_issues = closed_issues or 0

    if closed_issues == 0:
        return None

    return round(merged_prs / closed_issues, 4)
