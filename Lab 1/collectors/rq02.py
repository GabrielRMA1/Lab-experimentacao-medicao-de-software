def process_rq02(merged_prs_data: dict) -> int:
    if merged_prs_data and "totalCount" in merged_prs_data:
        return merged_prs_data["totalCount"]
    return 0