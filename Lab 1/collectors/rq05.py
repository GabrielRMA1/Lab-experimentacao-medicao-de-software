def process_rq05(primary_language_data: dict) -> str:
    if primary_language_data and "name" in primary_language_data:
        return primary_language_data["name"]
    return "Nao informada"
