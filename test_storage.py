import os
import sqlite3
import tempfile
import unittest

import storage

RECORDS = [
    {"machine": "A", "item": "Chips", "price_cents": 150, "quantity": 3,
     "date": "2026-10-17"},
    {"machine": "A", "item": "Soda", "price_cents": 125, "quantity": 4,
     "date": "2026-10-17"},
    {"machine": "B", "item": "Chips", "price_cents": 150, "quantity": 5,
     "date": "2026-10-17"},
]


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.folder.name, "sales.db")
        self.conn = storage.connect(self.db_path)

    def tearDown(self):
        # Windows cannot delete a database file that is still open.
        self.conn.close()
        self.folder.cleanup()

    def test_insert_returns_number_added(self):
        self.assertEqual(storage.insert_sales(self.conn, RECORDS), 3)
        self.assertEqual(len(storage.fetch_sales(self.conn)), 3)

    def test_second_insert_of_same_records_adds_nothing(self):
        storage.insert_sales(self.conn, RECORDS)
        self.assertEqual(storage.insert_sales(self.conn, RECORDS), 0)
        self.assertEqual(len(storage.fetch_sales(self.conn)), 3)

    def test_duplicate_inside_one_batch_is_ignored(self):
        added = storage.insert_sales(self.conn, [RECORDS[0], RECORDS[0]])
        self.assertEqual(added, 1)

    def test_same_item_on_new_date_is_a_new_row(self):
        storage.insert_sales(self.conn, RECORDS)
        next_day = dict(RECORDS[0])
        next_day["date"] = "2026-10-18"
        self.assertEqual(storage.insert_sales(self.conn, [next_day]), 1)

    def test_first_value_wins_when_key_repeats(self):
        storage.insert_sales(self.conn, [RECORDS[0]])
        changed = dict(RECORDS[0])
        changed["quantity"] = 99
        storage.insert_sales(self.conn, [changed])
        rows = storage.fetch_sales(self.conn)
        self.assertEqual(rows[0]["quantity"], 3)

    def test_data_survives_reopening_the_file(self):
        storage.insert_sales(self.conn, RECORDS)
        self.conn.close()
        self.conn = storage.connect(self.db_path)
        self.assertEqual(len(storage.fetch_sales(self.conn)), 3)

    def test_fetch_returns_dictionaries_in_insert_order(self):
        storage.insert_sales(self.conn, RECORDS)
        rows = storage.fetch_sales(self.conn)
        self.assertEqual(rows[1]["item"], "Soda")
        self.assertEqual(rows[1]["price_cents"], 125)

    def test_unique_key_is_in_the_table(self):
        storage.insert_sales(self.conn, [RECORDS[0]])
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                "INSERT INTO sales (machine, item, price_cents, quantity, date)"
                " VALUES ('A', 'Chips', 1, 1, '2026-10-17')")


class BadDatabaseTests(unittest.TestCase):
    def test_text_file_is_not_a_database(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "notes.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write("this is not a database, just some text " * 10)
            with self.assertRaises(sqlite3.DatabaseError):
                storage.connect(path)
            # Leaving the with block deletes the folder; on Windows that
            # only works because connect closed the file before raising.


if __name__ == "__main__":
    unittest.main()