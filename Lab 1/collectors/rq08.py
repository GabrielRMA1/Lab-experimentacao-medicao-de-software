def process_rq08(total_issues: int, stargazer_count: int) -> float:
    """Calcula a proporcao de issues em relacao ao tamanho da comunidade
    (issues por estrela). Mede o "atrito"/demanda de suporte relativo
    a popularidade do repositorio."""
    total_issues = total_issues or 0
    stargazer_count = stargazer_count or 0

    if stargazer_count == 0:
        return None

    razao = round(total_issues / stargazer_count, 4)
    return razao