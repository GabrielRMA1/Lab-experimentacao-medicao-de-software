from datetime import datetime, timezone


def process_rq01(created_at_str: str) -> dict:
    created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)

    dias = (now - created_at).days
    anos = round(dias / 365.25, 2)

    return {"idade_dias": dias, "idade_anos": anos}