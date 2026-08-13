import sys
import unittest
from pathlib import Path


SRC_DIR = Path(__file__).resolve().parents[1]

if str(SRC_DIR) not in sys.path:
    sys.path.append(str(SRC_DIR))

from collectors.rq05 import process_rq05
from collectors.rq06 import process_rq06
from collectors.rq07 import process_rq07


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


if __name__ == "__main__":
    unittest.main()
