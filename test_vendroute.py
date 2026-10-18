import contextlib
import io
import json
import os
import tempfile
import unittest

import vendroute

SALES = [
    {"machine": "A", "item": "Chips", "price_cents": 150, "quantity": 3,
     "date": "2026-10-17"},
    {"machine": "A", "item": "Soda", "price_cents": 125, "quantity": 4,
     "date": "2026-10-17"},
    {"machine": "B", "item": "Soda", "price_cents": 125, "quantity": 1,
     "date": "2026-10-17"},
    {"machine": "C", "item": "Soda", "price_cents": 200, "quantity": 2,
     "date": "2026-10-17"},
    {"machine": "B", "item": "Chips", "price_cents": -5, "quantity": 1,
     "date": "2026-10-17"},
    {"machine": "C", "item": "Chips", "quantity": 1, "date": "2026-10-17"},
]
class VendRouteTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.json_path = self.path("sales.json")
        self.db_path = self.path("sales.db")
        self.report_path = self.path("report.json")
        with open(self.json_path, "w", encoding="utf-8") as f:
            json.dump(SALES, f)

    def tearDown(self):
        self.folder.cleanup()

    def path(self, name):
        return os.path.join(self.folder.name, name)

    def run_tool(self, args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = vendroute.main(["vendroute.py"] + args)
        return code, out.getvalue()

    def run_normal(self):
        return self.run_tool([self.json_path, self.db_path, self.report_path])

    def test_success_prints_every_report(self):
        code, out = self.run_normal()
        self.assertEqual(code, 0)
        self.assertIn("Read 6 sales lines: 4 valid, 2 rejected", out)
        self.assertIn("line 5: price_cents must be positive (got -5)", out)
        self.assertIn("line 6: missing field 'price_cents'", out)
        self.assertIn("Inserted 4 new sales lines", out)
        self.assertIn("Machine A: 2 items, revenue $9.50", out)
        self.assertIn("Machine C, Soda on 2026-10-17: recorded $2.00, "
                      "expected $1.25", out)
        self.assertIn("  - Soda: sold 4, restock 4", out)

    def test_revenue_lines_in_descending_order(self):
        code, out = self.run_normal()
        a = out.index("Machine A: 2 items")
        c = out.index("Machine C: 1 item,")
        b = out.index("Machine B: 1 item,")
        self.assertTrue(a < c < b)

    def test_rerun_inserts_nothing_new(self):
        self.run_normal()
        code, out = self.run_normal()
        self.assertEqual(code, 0)
        self.assertIn("Inserted 0 new sales lines (4 skipped as duplicates)",
                      out)
        # Reports still describe the stored data, not just this run.
        self.assertIn("Machine A: 2 items, revenue $9.50", out)

    def test_report_file_written(self):
        self.run_normal()
        with open(self.report_path, "r", encoding="utf-8") as f:
            report = json.load(f)
        self.assertEqual(report["inserted"], 4)
        self.assertEqual(report["validation"]["rejected_count"], 2)
        self.assertEqual(report["revenue"][0]["machine"], "A")
        self.assertEqual(report["anomalies"][0]["machine"], "C")
        self.assertEqual(report["restock"]["A"][0],
                         {"item": "Soda", "sold": 4, "restock": 4})

    def test_malformed_json_exits_with_1_and_clear_message(self):
        with open(self.json_path, "w", encoding="utf-8") as f:
            f.write('[{"machine": "A",}]')
        code, out = self.run_normal()
        self.assertEqual(code, 1)
        self.assertTrue(out.startswith("Error: malformed JSON"))
        self.assertNotIn("Traceback", out)
        self.assertFalse(os.path.exists(self.db_path))
        self.assertFalse(os.path.exists(self.report_path))

    def test_missing_file_exits_with_1(self):
        code, out = self.run_tool([self.path("nope.json"), self.db_path])
        self.assertEqual(code, 1)
        self.assertIn("file not found", out)

    def test_swapped_arguments_give_clear_errors(self):
        self.run_normal()
        code, out = self.run_tool([self.db_path, self.json_path])
        self.assertEqual(code, 1)
        # Depending on its bytes, the database is either not text or not JSON.
        self.assertTrue(out.startswith("Error: "))
        self.assertNotIn("Traceback", out)

    def test_json_file_used_as_database(self):
        code, out = self.run_tool([self.json_path, self.json_path])
        self.assertEqual(code, 1)
        self.assertIn("Error: cannot use database", out)
        self.assertNotIn("Report saved", out)

    def test_database_in_missing_folder(self):
        db_path = os.path.join(self.folder.name, "no_such_folder", "s.db")
        code, out = self.run_tool([self.json_path, db_path])
        self.assertEqual(code, 1)
        self.assertIn("Error: cannot use database", out)

    def test_report_that_cannot_be_written(self):
        code, out = self.run_tool(
            [self.json_path, self.db_path, self.folder.name])
        self.assertEqual(code, 1)
        self.assertIn("Error: cannot write report", out)

    def test_wrong_number_of_arguments_shows_usage(self):
        code, out = self.run_tool([self.json_path])
        self.assertEqual(code, 1)
        self.assertIn("Usage:", out)


if __name__ == "__main__":
    unittest.main()