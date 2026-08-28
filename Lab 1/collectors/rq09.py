from datetime import datetime

def process_rq09(created_at_str: str, pushed_at_str: str):
    """Calcula em dias o periodo entre a criacao e a ultima atividade."""
    if not created_at_str or not pushed_at_str:
        return None

    created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
    pushed_at = datetime.fromisoformat(pushed_at_str.replace("Z", "+00:00"))

    return (pushed_at - created_at).total_seconds() / 86400