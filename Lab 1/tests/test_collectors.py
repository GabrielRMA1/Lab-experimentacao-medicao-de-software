import sys
import unittest
from pathlib import Path


SRC_DIR = Path(__file__).resolve().parents[1]

if str(SRC_DIR) not in sys.path:
    sys.path.append(str(SRC_DIR))

from collectors.rq05 import process_rq05
from collectors.rq06 import process_rq06
from collectors.rq07 import process_rq07
from analysis_rqs import get_iqr_outliers
from project_v2_snapshot import get_status, normalize_item


class TestCollectors(unittest.TestCase):
    def test_process_rq05_returns_primary_language(self):
        self.assertEqual(process_rq05({"name": "Python"}), "Python")

    def test_process_rq05_handles_missing_language(self):
        self.assertEqual(process_rq05(None), "Nao informada")

    def test_process_rq06_returns_stargazer_count(self):
        self.assertEqual(process_rq06(1500), 1500)

    def test_process_rq06_handles_missing_stargazer_count(self):
        self.assertEqual(process_rq06(None), 0)

    def test_process_rq07_calculates_issue_metrics(self):
        result = process_rq07({"totalCount": 20}, {"totalCount": 5})

        self.assertEqual(result["total_issues"], 20)
        self.assertEqual(result["issues_fechadas"], 5)
        self.assertEqual(result["percentual_issues_fechadas"], 25.0)

    def test_process_rq07_handles_zero_issues(self):
        result = process_rq07({"totalCount": 0}, {"totalCount": 0})

        self.assertEqual(result["percentual_issues_fechadas"], 0)

    def test_get_iqr_outliers_counts_extreme_values(self):
        import pandas as pd

        df = pd.DataFrame({"estrelas": [10, 11, 12, 13, 1000]})
        result = get_iqr_outliers(df, "estrelas")

        self.assertEqual(result["outliers"], 1)

    def test_project_v2_status_is_extracted_from_status_field(self):
        item = {
            "fieldValues": {
                "nodes": [
                    {"name": "Alta", "field": {"name": "Prioridade"}},
                    {"name": "In progress", "field": {"name": "Status"}},
                ]
            }
        }

        self.assertEqual(get_status(item), "In progress")

    def test_project_v2_item_is_normalized_for_csv(self):
        item = {
            "id": "PVTI_123",
            "type": "ISSUE",
            "content": {
                "title": "Criar coleta",
                "number": 7,
                "state": "OPEN",
                "url": "https://github.com/a/b/issues/7",
                "repository": {"nameWithOwner": "a/b"},
            },
            "fieldValues": {
                "nodes": [{"name": "Done", "field": {"name": "Status"}}]
            },
        }

        row = normalize_item("Lab Project", item)

        self.assertEqual(row["project"], "Lab Project")
        self.assertEqual(row["title"], "Criar coleta")
        self.assertEqual(row["status"], "Done")
        self.assertEqual(row["repository"], "a/b")


if __name__ == "__main__":
    unittest.main()
