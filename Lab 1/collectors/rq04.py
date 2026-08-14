from datetime import datetime, timezone


def process_rq04(repository):
    updated_at = repository["pushedAt"]

    updated = datetime.fromisoformat(
        updated_at.replace("Z", "+00:00")
    )

    now = datetime.now(timezone.utc)

    return (now - updated).total_seconds() / 86400