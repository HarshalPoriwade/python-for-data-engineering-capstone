import unittest

import reports


def sale(machine, item, price_cents, quantity, date="2026-10-17"):
    return {"machine": machine, "item": item, "price_cents": price_cents,
            "quantity": quantity, "date": date}


class FormatTests(unittest.TestCase):
    def test_format_dollars(self):
        self.assertEqual(reports.format_dollars(1250), "$12.50")
        self.assertEqual(reports.format_dollars(5), "$0.05")
        self.assertEqual(reports.format_dollars(0), "$0.00")

    def test_format_quantity(self):
        self.assertEqual(reports.format_quantity(3.0), "3")
        self.assertEqual(reports.format_quantity(2.5), "2.5")


class RevenueTests(unittest.TestCase):
    def test_sorted_by_revenue_descending(self):
        sales = [
            sale("A", "Chips", 150, 2),
            sale("B", "Chips", 150, 10),
            sale("C", "Soda", 100, 5),
        ]
        machines = [r["machine"] for r in reports.revenue_per_machine(sales)]
        self.assertEqual(machines, ["B", "C", "A"])

    def test_counts_distinct_items_and_sums_revenue(self):
        sales = [
            sale("A", "Chips", 150, 3),
            sale("A", "Chips", 150, 2, "2026-10-18"),
            sale("A", "Soda", 125, 4),
            sale("A", "Candy", 100, 0.5),
        ]
        result = reports.revenue_per_machine(sales)
        self.assertEqual(result, [
            {"machine": "A", "items": 3, "revenue_cents": 750 + 500 + 50}])

    def test_ties_sorted_by_machine_name(self):
        sales = [sale("Z", "Chips", 100, 1), sale("M", "Chips", 100, 1)]
        machines = [r["machine"] for r in reports.revenue_per_machine(sales)]
        self.assertEqual(machines, ["M", "Z"])

    def test_no_sales(self):
        self.assertEqual(reports.revenue_per_machine([]), [])


class AnomalyTests(unittest.TestCase):
    def test_expected_price_is_most_common(self):
        sales = [
            sale("A", "Soda", 125, 1),
            sale("B", "Soda", 125, 1),
            sale("C", "Soda", 200, 1),
        ]
        self.assertEqual(reports.expected_prices(sales), {"Soda": 125})

    def test_tie_takes_lowest_price(self):
        sales = [sale("A", "Water", 100, 1), sale("B", "Water", 60, 1)]
        self.assertEqual(reports.expected_prices(sales), {"Water": 60})

    def test_flags_price_more_than_20_percent_off(self):
        sales = [
            sale("A", "Soda", 125, 1),
            sale("B", "Soda", 125, 1),
            sale("C", "Soda", 200, 1),
        ]
        self.assertEqual(reports.find_anomalies(sales), [{
            "machine": "C", "item": "Soda", "date": "2026-10-17",
            "recorded_cents": 200, "expected_cents": 125}])

    def test_flags_low_prices_too(self):
        sales = [sale("A", "Chips", 100, 1), sale("B", "Chips", 100, 1),
                 sale("C", "Chips", 79, 1)]
        flagged = [a["machine"] for a in reports.find_anomalies(sales)]
        self.assertEqual(flagged, ["C"])

    def test_exactly_20_percent_is_not_flagged(self):
        sales = [sale("A", "Chips", 100, 1), sale("B", "Chips", 100, 1),
                 sale("C", "Chips", 120, 1), sale("D", "Chips", 80, 1)]
        self.assertEqual(reports.find_anomalies(sales), [])

    def test_just_over_20_percent_is_flagged(self):
        sales = [sale("A", "Chips", 150, 1), sale("B", "Chips", 150, 1),
                 sale("C", "Chips", 181, 1)]
        self.assertEqual(len(reports.find_anomalies(sales)), 1)

    def test_prices_compared_per_item(self):
        sales = [sale("A", "Chips", 150, 1), sale("A", "Candy", 100, 1)]
        self.assertEqual(reports.find_anomalies(sales), [])


class RestockTests(unittest.TestCase):
    def test_items_sorted_by_quantity_sold(self):
        sales = [
            sale("A", "Chips", 150, 3),
            sale("A", "Soda", 125, 4),
            sale("A", "Chips", 150, 2, "2026-10-18"),
            sale("A", "Candy", 100, 1),
        ]
        notes = reports.restock_notes(sales)
        self.assertEqual(notes, {"A": [
            {"item": "Chips", "sold": 5, "restock": 5},
            {"item": "Soda", "sold": 4, "restock": 4},
            {"item": "Candy", "sold": 1, "restock": 1},
        ]})

    def test_fractional_quantity_rounds_up(self):
        notes = reports.restock_notes([sale("A", "Coffee", 200, 2.25)])
        self.assertEqual(notes["A"][0]["restock"], 3)
        self.assertEqual(notes["A"][0]["sold"], 2.25)

    def test_float_sum_noise_does_not_add_a_unit(self):
        # pandas adds these up to 3.0000000000000004, not 3.0.
        sales = [sale("A", "Coffee", 200, 0.2, "d1"),
                 sale("A", "Coffee", 200, 2.2, "d2"),
                 sale("A", "Coffee", 200, 0.6, "d3")]
        note = reports.restock_notes(sales)["A"][0]
        self.assertEqual(note["restock"], 3)
        self.assertEqual(note["sold"], 3)

    def test_one_note_per_machine(self):
        sales = [sale("B", "Chips", 150, 1), sale("A", "Chips", 150, 1)]
        self.assertEqual(list(reports.restock_notes(sales)), ["A", "B"])

    def test_no_sales(self):
        self.assertEqual(reports.restock_notes([]), {})


class BuildReportTests(unittest.TestCase):
    def test_report_has_every_section(self):
        report = reports.build_report(
            [{"line": 2, "reason": "x"}], 1, [sale("A", "Chips", 150, 1)])
        self.assertEqual(report["validation"]["rejected_count"], 1)
        self.assertEqual(report["inserted"], 1)
        self.assertEqual(len(report["revenue"]), 1)
        self.assertEqual(report["anomalies"], [])
        self.assertIn("A", report["restock"])


if __name__ == "__main__":
    unittest.main()