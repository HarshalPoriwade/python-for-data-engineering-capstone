import os
import tempfile
import unittest

import validator


def good_record():
    return {"machine": "A", "item": "Chips", "price_cents": 150,
            "quantity": 3, "date": "2026-10-17"}


class CheckRecordTests(unittest.TestCase):
    def test_good_record_has_no_problems(self):
        self.assertEqual(validator.check_record(good_record()), [])

    def test_each_missing_field_is_reported(self):
        for field in validator.REQUIRED_FIELDS:
            record = good_record()
            del record[field]
            self.assertEqual(validator.check_record(record),
                             ["missing field '" + field + "'"])

    def test_blank_text_counts_as_missing(self):
        record = good_record()
        record["machine"] = "   "
        self.assertEqual(validator.check_record(record),
                         ["missing field 'machine'"])

    def test_zero_and_negative_price_rejected(self):
        for price in [0, -50]:
            record = good_record()
            record["price_cents"] = price
            reasons = validator.check_record(record)
            self.assertEqual(len(reasons), 1)
            self.assertIn("price_cents must be positive", reasons[0])

    def test_zero_and_negative_quantity_rejected(self):
        for quantity in [0, -2, -0.5]:
            record = good_record()
            record["quantity"] = quantity
            reasons = validator.check_record(record)
            self.assertEqual(len(reasons), 1)
            self.assertIn("quantity must be positive", reasons[0])

    def test_text_price_rejected(self):
        record = good_record()
        record["price_cents"] = "150"
        self.assertEqual(validator.check_record(record),
                         ["price_cents must be a whole number"])

    def test_fractional_price_rejected_but_whole_float_allowed(self):
        record = good_record()
        record["price_cents"] = 150.5
        self.assertEqual(validator.check_record(record),
                         ["price_cents must be a whole number"])
        record["price_cents"] = 150.0
        self.assertEqual(validator.check_record(record), [])

    def test_boolean_is_not_a_number(self):
        record = good_record()
        record["quantity"] = True
        self.assertEqual(validator.check_record(record),
                         ["quantity must be a number"])

    def test_nan_price_rejected_without_crashing(self):
        record = good_record()
        record["price_cents"] = float("nan")
        self.assertEqual(validator.check_record(record),
                         ["price_cents must be a whole number"])

    def test_fractional_quantity_allowed(self):
        record = good_record()
        record["quantity"] = 2.5
        self.assertEqual(validator.check_record(record), [])

    def test_non_object_record(self):
        self.assertEqual(validator.check_record(["A", "Chips"]),
                         ["record is not a JSON object"])

    def test_several_problems_reported_together(self):
        record = {"machine": "A", "price_cents": -1, "quantity": 0,
                  "date": "2026-10-17"}
        reasons = validator.check_record(record)
        self.assertEqual(len(reasons), 3)


class ValidateRecordsTests(unittest.TestCase):
    def test_line_numbers_start_at_one(self):
        bad = good_record()
        bad["quantity"] = 0
        valid, rejected = validator.validate_records(
            [good_record(), bad, good_record()])
        self.assertEqual(len(valid), 2)
        self.assertEqual(rejected, [
            {"line": 2, "reason": "quantity must be positive (got 0)"}])

    def test_valid_text_is_stripped(self):
        record = good_record()
        record["item"] = "  Chips "
        valid, rejected = validator.validate_records([record])
        self.assertEqual(valid[0]["item"], "Chips")


class LoadRecordsTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.folder.name, "sales.json")

    def tearDown(self):
        self.folder.cleanup()

    def write(self, text, encoding="utf-8"):
        with open(self.path, "w", encoding=encoding) as f:
            f.write(text)

    def test_reads_a_list(self):
        self.write('[{"machine": "A"}]')
        self.assertEqual(validator.load_records(self.path), [{"machine": "A"}])

    def test_reads_file_with_byte_order_mark_and_crlf(self):
        self.write('[\r\n{"machine": "A"}\r\n]\r\n', encoding="utf-8-sig")
        self.assertEqual(validator.load_records(self.path), [{"machine": "A"}])

    def test_malformed_json_raises_with_line_number(self):
        self.write('[\n{"machine": "A"}\n{"machine": "B"}\n]')
        with self.assertRaises(validator.SalesFileError) as ctx:
            validator.load_records(self.path)
        self.assertIn("malformed JSON", str(ctx.exception))
        self.assertIn("line 3", str(ctx.exception))

    def test_top_level_object_is_rejected(self):
        self.write('{"machine": "A"}')
        with self.assertRaises(validator.SalesFileError):
            validator.load_records(self.path)

    def test_missing_file(self):
        with self.assertRaises(validator.SalesFileError) as ctx:
            validator.load_records(os.path.join(self.folder.name, "nope.json"))
        self.assertIn("file not found", str(ctx.exception))

    def test_binary_file_is_rejected_cleanly(self):
        with open(self.path, "wb") as f:
            f.write(b"SQLite format 3\x00\xff\xfe")
        with self.assertRaises(validator.SalesFileError) as ctx:
            validator.load_records(self.path)
        self.assertIn("not a JSON text file", str(ctx.exception))

    def test_folder_instead_of_file(self):
        with self.assertRaises(validator.SalesFileError) as ctx:
            validator.load_records(self.folder.name)
        self.assertIn("cannot read", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()